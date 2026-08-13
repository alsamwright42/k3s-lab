#!/usr/bin/env python3
import os
import sys
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

# 1. Resolve the folder containing this test file ({repo_root}/tests)
test_dir = Path(__file__).resolve().parent

# 2. Step up to the repository root and descend into the workstation scripts directory [2]
scripts_dir = test_dir.parent / "scripts" / "workstation"

# 3. Inject the path at the very front of Python's search path
sys.path.insert(0, str(scripts_dir))

# 4. Natively import the unversioned script!
import query_gemini_review as query_gemini_review

class TestQueryGeminiReview(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gemini-review-test-")
        self.diff_path = os.path.join(self.temp_dir, "test.diff")
        self.output_path = os.path.join(self.temp_dir, "output.json")
        os.environ["GEMINI_API_KEY"] = "fake-key"
        os.environ["GEMINI_DIFF_PATH"] = self.diff_path
        os.environ["GEMINI_OUTPUT_PATH"] = self.output_path

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GEMINI_DIFF_PATH", None)
        os.environ.pop("GEMINI_OUTPUT_PATH", None)

    def write_diff(self, content):
        with open(self.diff_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_sanitize_json_response(self):
        # Test cleaning of markdown wrap failures
        raw = "```json\n{\n  \"comments\": []\n}\n```"
        self.assertEqual(query_gemini_review.sanitize_json_response(raw), "{\n  \"comments\": []\n}")
        
        raw_clean = "{\n  \"comments\": []\n}"
        self.assertEqual(query_gemini_review.sanitize_json_response(raw_clean), raw_clean)

    def test_parse_diff_to_changes_list(self):
        diff = (
            "--- a/Makefile\n"
            "+++ b/Makefile\n"
            "@@ -10,3 +10,4 @@\n"
            " un-changed\n"
            "+added line 1\n"
            "+added line 2\n"
        )
        res = query_gemini_review.parse_diff_to_changes_list(diff)
        self.assertIn("=== FILE: Makefile ===", res)
        self.assertIn("Line 11: added line 1", res)
        self.assertIn("Line 12: added line 2", res)

    @patch("urllib.request.urlopen")
    def test_successful_review_classification(self, mock_urlopen):
        # Setup valid unified diff content
        self.write_diff(
            "--- a/Makefile\n"
            "+++ b/Makefile\n"
            "@@ -1,1 +1,2 @@\n"
            "+CLEAN_ENV := /tmp/clean.env\n"
        )
        
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        
        mock_api_payload = {
            "candidates": [{
                "content": {
                    "parts": [{"text": json.dumps({
                        "comments": [
                            {
                                "file": "Makefile",
                                "line": 1,
                                "severity": "WARNING",
                                "message": "Static warning"
                            }
                        ]
                    })}]
                }
            }]
        }
        mock_response.read.return_value = json.dumps(mock_api_payload).encode("utf-8")
        mock_urlopen.return_value = mock_response

        # Execute
        with patch("sys.argv", ["query-gemini-review.py"]):
            query_gemini_review.main()

        # Assert output was saved and contains the severity
        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.assertEqual(len(data["comments"]), 1)
        self.assertEqual(data["comments"][0]["severity"], "WARNING")

    def test_filter_suppressed_comments(self):
        # Create a mock file on disk that contains '# ai-ignore'
        target_file = os.path.join(self.temp_dir, "bootstrap.sh")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write("sed -i 's/\\r$//' script.sh # ai-ignore: false-positive\n")
            f.write("echo 'done'\n")

        review_data = {
            "comments": [
                {
                    "file": "bootstrap.sh",
                    "line": 2,
                    "severity": "WARNING",
                    "message": "Do not use sed -i"
                },
                {
                    "file": "bootstrap.sh",
                    "line": 3,
                    "severity": "WARNING",
                    "message": "Stylistic warning"
                }
            ]
        }

        filtered = query_gemini_review.filter_suppressed_comments(review_data, repo_root=self.temp_dir)
        
        # Line 2 has # ai-ignore, so it must be stripped. Line 3 does not, so it is preserved.
        self.assertEqual(len(filtered["comments"]), 1)
        self.assertEqual(filtered["comments"][0]["line"], 3)

    @patch("urllib.request.urlopen")
    def test_transient_error_handling_with_retry(self, mock_urlopen):
        # Setup valid unified diff content
        self.write_diff(
            "--- a/Makefile\n"
            "+++ b/Makefile\n"
            "@@ -1,1 +1,2 @@\n"
            "+CLEAN_ENV := /tmp/clean.env\n"
        )
        
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        
        mock_api_payload = {
            "candidates": [{
                "content": {
                    "parts": [{"text": json.dumps({"comments": []})}]
                }
            }]
        }
        mock_response.read.return_value = json.dumps(mock_api_payload).encode("utf-8")

        # Mock urlopen to raise a 503 HTTPError first, then succeed
        mock_urlopen.side_effect = [
            urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None),
            mock_response
        ]

        # Patch time.sleep to avoid slowing down tests
        with patch("time.sleep"), patch("sys.argv", ["query-gemini-review.py"]):
            query_gemini_review.main()

        # Should exit cleanly and call urlopen twice
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertTrue(os.path.exists(self.output_path))

if __name__ == "__main__":
    unittest.main()
