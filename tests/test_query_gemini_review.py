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
if scripts_dir.exists():
    sys.path.insert(0, str(scripts_dir))
else:
    # Sandbox fallback / local staging runner fallback
    sys.path.insert(0, str(test_dir))

# 4. Natively import the unversioned script!
import query_gemini_review

class TestQueryGeminiReview(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary directory mimicking the Git repository
        self.temp_dir = tempfile.mkdtemp(prefix="gemini-review-test-")
        self.diff_path = os.path.join(self.temp_dir, "test.diff")
        self.output_path = os.path.join(self.temp_dir, "output.json")
        
        # Configure standard environment baseline
        os.environ["GEMINI_API_KEY"] = "fake-key"
        os.environ["GEMINI_DIFF_PATH"] = self.diff_path
        os.environ["GEMINI_OUTPUT_PATH"] = self.output_path

    def tearDown(self):
        # Clean up temporary directories and pop environments cleanly
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
        self.assertEqual(data["comments"][0]["file"], "Makefile")

    @patch("urllib.request.urlopen")
    def test_successful_api_review_via_env_vars(self, mock_urlopen):
        """Verify a successful API request using environment variables instead of CLI args."""
        self.write_diff(
            "--- a/Makefile\n"
            "+++ b/Makefile\n"
            "@@ -1,1 +1,2 @@\n"
            "+CLEAN_ENV := /tmp/clean.env\n"
        )
        
        # Mock API Response
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_api_payload = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "comments": [
                                {
                                    "file": "Makefile",
                                    "line": 1,
                                    "severity": "WARNING",
                                    "message": "Avoid raw shell commands"
                                }
                            ]
                        })
                    }]
                }
            }]
        }
        mock_response.read.return_value = json.dumps(mock_api_payload).encode("utf-8")
        mock_urlopen.return_value = mock_response

        test_args = ["query_gemini_review.py"]
        with patch.object(sys, "argv", test_args):
            query_gemini_review.main()
                
        # Confirm output is structured exactly as received from Gemini
        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.assertEqual(len(data["comments"]), 1)
        self.assertEqual(data["comments"][0]["file"], "Makefile")

    @patch("urllib.request.urlopen")
    def test_api_http_error_handling_fails_permanently_on_fatal_403(self, mock_urlopen):
        """Verify that a fatal 403 Forbidden HTTPError does not trigger retries and exits with status 1."""
        self.write_diff(
            "--- a/Makefile\n"
            "+++ b/Makefile\n"
            "@@ -1,1 +1,2 @@\n"
            "+CLEAN_ENV := /tmp/clean.env\n"
        )
        
        test_args = [
            "query_gemini_review.py",
            "--diff-path", self.diff_path,
            "--output-path", self.output_path
        ]
        
        # Simulate a 403 Forbidden HTTP Error
        mock_error = urllib.error.HTTPError(
            url="http://google.com",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=MagicMock()
        )
        mock_error.read = MagicMock(return_value=b"Invalid Key")
        mock_urlopen.side_effect = mock_error
        
        with patch.object(sys, "argv", test_args):
            with self.assertRaises(SystemExit) as cm:
                query_gemini_review.main()
            self.assertEqual(cm.exception.code, 1)
            # urlopen should only be called once because 403 is non-retryable
            self.assertEqual(mock_urlopen.call_count, 1)

    @patch("urllib.request.urlopen")
    def test_custom_model_and_api_version(self, mock_urlopen):
        """Verify that custom model and api version CLI flags correctly shape the request URL."""
        self.write_diff(
            "--- a/Makefile\n"
            "+++ b/Makefile\n"
            "@@ -1,1 +1,2 @@\n"
            "+CLEAN_ENV := /tmp/clean.env\n"
        )

        test_args = [
            "query_gemini_review.py",
            "--diff-path", self.diff_path,
            "--output-path", self.output_path,
            "--model", "gemini-3.5-pro",
            "--api-version", "v1"
        ]

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
        mock_urlopen.return_value = mock_response

        with patch.object(sys, "argv", test_args):
            query_gemini_review.main()

        # Extract the Request object that was passed to urlopen
        called_req = mock_urlopen.call_args[0][0]
        self.assertIn("v1/models/gemini-3.5-pro:generateContent", called_req.full_url)

    def test_filter_suppressed_comments(self):
        """Verify that filter_suppressed_comments strips comments for lines containing 'ai-ignore'."""
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
    @patch("time.sleep")  # Prevent sleeping during testing to speed it up
    def test_transient_error_handling_with_retry(self, mock_sleep, mock_urlopen):
        """Verify that a transient 503 error triggers retries and succeeds once the API responds."""
        # Setup valid unified diff content
        self.write_diff(
            "--- a/Makefile\n"
            "+++ b/Makefile\n"
            "@@ -1,1 +1,2 @@\n"
            "+CLEAN_ENV := /tmp/clean.env\n"
        )

        test_args = [
            "query_gemini_review.py",
            "--diff-path", self.diff_path,
            "--output-path", self.output_path
        ]

        # First call returns 503 HTTPError
        mock_error = urllib.error.HTTPError(
            url="http://google.com",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=MagicMock()
        )
        mock_error.read = MagicMock(return_value=b"Temporary Overload")

        # Second call returns 200 OK
        mock_success_response = MagicMock()
        mock_success_response.__enter__.return_value = mock_success_response
        mock_api_payload = {
            "candidates": [{
                "content": {
                    "parts": [{"text": json.dumps({"comments": []})}]
                }
            }]
        }
        mock_success_response.read.return_value = json.dumps(mock_api_payload).encode("utf-8")

      # Set side effect: first raise HTTPError, then return successful response
        mock_urlopen.side_effect = [mock_error, mock_success_response]

        with patch.object(sys, "argv", test_args):
            query_gemini_review.main()

        # Assertions
        self.assertEqual(mock_urlopen.call_count, 2)  # Proves retry occurred
        self.assertEqual(mock_sleep.call_count, 1)    # Proves backoff sleep happened  
        self.assertTrue(os.path.exists(self.output_path))

if __name__ == "__main__":
    unittest.main()
