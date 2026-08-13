import os
import sys
import json
import urllib.request
import urllib.error
import unittest
import tempfile
import shutil
import importlib.util
from unittest.mock import patch, MagicMock

class TestQueryGeminiReviewV6(unittest.TestCase):
    def setUp(self):
        # Create a temporary workspace directory
        self.test_dir = tempfile.mkdtemp()
        self.repo_root = os.path.realpath(self.test_dir)
        
         # Dynamically find the script path under test
        test_dir_path = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(test_dir_path) if os.path.basename(test_dir_path) == "tests" else test_dir_path
        
        possible_paths = [
            os.path.join(parent_dir, "scripts", "workstation", "query-gemini-review.py"),
            os.path.realpath("/workspace/scratch/query-gemini-review-v3.py"),
            os.path.realpath("./query-gemini-review-v3.py"),
        ]
        
        self.script_path = None
        for path in possible_paths:
            if os.path.exists(path):
                self.script_path = path
                break
                
        if not self.script_path:
            raise FileNotFoundError(f"Could not find query-gemini-review script under test in possible paths: {possible_paths}")
             
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("query_gemini_v6", self.script_path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.test_dir)

    @patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_missing_api_key_exits(self):
        """Verify that the script exits with code 1 if GEMINI_API_KEY is not set."""
        with patch.object(sys, "argv", ["query-gemini-review-v6.py"]):
            with self.assertRaises(SystemExit) as cm:
                self.module.main()
            self.assertEqual(cm.exception.code, 1)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_missing_diff_file_creates_default_json_and_returns(self):
        """Verify that if the diff file is missing, it creates a default empty json and returns gracefully."""
        diff_path = os.path.join(self.repo_root, "missing_diff.diff")
        output_path = os.path.join(self.repo_root, "output.json")
        
        # Execute using CLI arguments
        test_args = [
            "query-gemini-review-v6.py",
            "--diff-path", diff_path,
            "--output-path", output_path
        ]
        
        with patch.object(sys, "argv", test_args):
            self.module.main()
            
        # Verify output exists and is an empty comments array
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data, {"comments": []})

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_empty_diff_file_returns_immediately(self):
        """Verify that if the diff file is empty, it returns immediately without hitting the API."""
        diff_path = os.path.join(self.repo_root, "empty_diff.diff")
        output_path = os.path.join(self.repo_root, "output.json")
        
        with open(diff_path, "w") as f:
            f.write("")  # Empty diff file
            
        test_args = [
            "query-gemini-review-v6.py",
            "--diff-path", diff_path,
            "--output-path", output_path
        ]
        
        # Mock urllib.request.urlopen to ensure it is NEVER called
        with patch("urllib.request.urlopen") as mock_url:
            with patch.object(sys, "argv", test_args):
                self.module.main()
            mock_url.assert_not_called()
            
        # Verify output file exists with default empty schema
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data, {"comments": []})

    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_DIFF_PATH": "env_diff.diff",
        "GEMINI_OUTPUT_PATH": "env_output.json"
    })
    @patch("urllib.request.urlopen")
    def test_successful_api_review_via_env_vars(self, mock_urlopen):
        """Verify a successful API request using environment variables instead of CLI args."""
        # Standardize local test paths based on env vars
        diff_path = os.path.join(self.repo_root, "env_diff.diff")
        output_path = os.path.join(self.repo_root, "env_output.json")
        
        # Write valid git diff
        with open(diff_path, "w") as f:
            f.write("+ test addition line")
            
        # Mock API Response
        mock_response = MagicMock()
        mock_api_payload = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "comments": [
                                {
                                    "file": "Makefile",
                                    "line": 5,
                                    "message": "⚠️ Avoid raw shell commands without POSIX checking."
                                }
                            ]
                        })
                    }]
                }
            }]
        }
        mock_response.read.return_value = json.dumps(mock_api_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Execute main with patched sys.argv, using env-vars for path lookup
        test_args = ["query-gemini-review-v6.py"]
        with patch.dict(os.environ, {
            "GEMINI_DIFF_PATH": diff_path,
            "GEMINI_OUTPUT_PATH": output_path
        }):
            with patch.object(sys, "argv", test_args):
                self.module.main()
                
        # Confirm output is structured exactly as received from Gemini
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, "r") as f:
            data = json.load(f)
            
        self.assertEqual(len(data["comments"]), 1)
        self.assertEqual(data["comments"][0]["file"], "Makefile")
        self.assertEqual(data["comments"][0]["line"], 5)
        self.assertIn("Avoid raw shell commands", data["comments"][0]["message"])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("urllib.request.urlopen")
    def test_api_http_error_handling(self, mock_urlopen):
        """Verify HTTPError exits with status 1."""
        diff_path = os.path.join(self.repo_root, "err_diff.diff")
        output_path = os.path.join(self.repo_root, "err_output.json")
        
        with open(diff_path, "w") as f:
            f.write("+ mock diff change")
            
        test_args = [
            "query-gemini-review-v6.py",
            "--diff-path", diff_path,
            "--output-path", output_path
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
                self.module.main()
            self.assertEqual(cm.exception.code, 1)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("urllib.request.urlopen")
    def test_custom_model_and_api_version(self, mock_urlopen):
        """Verify that custom model and api version CLI flags correctly shape the request URL."""
        diff_path = os.path.join(self.repo_root, "custom_diff.diff")
        output_path = os.path.join(self.repo_root, "custom_output.json")
        
        with open(diff_path, "w") as f:
            f.write("+ mock diff change")

        test_args = [
            "query-gemini-review-v6.py",
            "--diff-path", diff_path,
            "--output-path", output_path,
            "--model", "gemini-3.5-pro",
            "--api-version", "v1"
        ]

        mock_response = MagicMock()
        mock_api_payload = {
            "candidates": [{
                "content": {
                    "parts": [{"text": json.dumps({"comments": []})}]
                }
            }]
        }
        mock_response.read.return_value = json.dumps(mock_api_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch.object(sys, "argv", test_args):
            self.module.main()

        # Extract the Request object that was passed to urlopen
        called_req = mock_urlopen.call_args[0][0]
        self.assertIn("v1/models/gemini-3.5-pro:generateContent", called_req.full_url)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("urllib.request.urlopen")
    def test_default_model_and_api_version(self, mock_urlopen):
        """Verify that default values for model (gemini-3.5-flash) and api_version (v1beta) are correctly resolved."""
        diff_path = os.path.join(self.repo_root, "default_diff.diff")
        output_path = os.path.join(self.repo_root, "default_output.json")
        
        with open(diff_path, "w") as f:
            f.write("+ mock diff change")

        test_args = [
            "query-gemini-review-v6.py",
            "--diff-path", diff_path,
            "--output-path", output_path
        ]

        mock_response = MagicMock()
        mock_api_payload = {
            "candidates": [{
                "content": {
                    "parts": [{"text": json.dumps({"comments": []})}]
                }
            }]
        }
        mock_response.read.return_value = json.dumps(mock_api_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch.object(sys, "argv", test_args):
            self.module.main()

        # Extract the Request object that was passed to urlopen
        called_req = mock_urlopen.call_args[0][0]
        self.assertIn("v1beta/models/gemini-3.5-flash:generateContent", called_req.full_url)

if __name__ == "__main__":
    unittest.main()
