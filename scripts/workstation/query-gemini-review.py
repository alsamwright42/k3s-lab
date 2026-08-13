#!/usr/bin/env python3
import os
import sys
import json
import argparse
import urllib.request
import urllib.error

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract Git diff and consult Gemini for secure homelab code review annotations."
    )
    parser.add_argument(
        "--diff-path",
        default=os.environ.get("GEMINI_DIFF_PATH", "pr_changes.diff"),
        help="Path to the input Git diff file (default: 'pr_changes.diff' or GEMINI_DIFF_PATH env var)"
    )
    parser.add_argument(
        "--output-path",
        default=os.environ.get("GEMINI_OUTPUT_PATH", "review_output.json"),
        help="Path to save the generated JSON review findings (default: 'review_output.json' or GEMINI_OUTPUT_PATH env var)"
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        help="Gemini model version (default: 'gemini-3.5-flash' or GEMINI_MODEL env var)"
    )
    parser.add_argument(
        "--api-version",
        default=os.environ.get("GEMINI_API_VERSION", "v1beta"),
        help="Gemini api version used in gemini url (default: 'v1beta' or GEMINI_API_VERSION env var)"
    )    
    return parser.parse_args()

def main():
    args = parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    diff_path = args.diff_path
    output_path = args.output_path
    api_version = args.api_version
    model = args.model

    # Initialize default empty comments file to ensure downstream steps don't crash
    default_output = {"comments": []}
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    except Exception:
        pass  # If path is flat/current directory, avoid failing

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(default_output, f, indent=2)

    if not os.path.exists(diff_path):
        print(f"⚠️ Warning: Input diff file '{diff_path}' not found. Skipping analysis.", file=sys.stderr)
        return

    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read().strip()

    if not diff_content:
        print(f"✅ PR Diff '{diff_path}' is empty. No changes to analyze.")
        return
    # Prompt engineered to guide the model to perform a rigid code quality & security review
    prompt = (
        "You are an expert DevOps and Platform Engineer auditing code quality, syntax, "
        "security (credential leaks), and architectural anti-patterns in a Kubernetes homelab. "
        "Analyze the following Git diff of a Pull Request. Focus on:\n"
        "1. POSIX-safe shell scripting (avoiding bash-isms like '&>' in standard /bin/sh recipes).\n"
        "2. Safe environment sourcing and dynamic configurations in Makefiles.\n"
        "3. Terraform module declarations, ensuring required arguments are populated and secrets are sensitive.\n"
        "4. Kubernetes manifest security (avoiding hardcoded secrets or privileged contexts).\n\n"
        "You must return your output strictly in JSON format. Do not wrap your response in markdown code blocks. "
        "The JSON structure must match this exact schema:\n"
        "{\n"
        "  \"comments\": [\n"
        "    { \"file\": \"filename\", \"line\": line_number_integer, \"message\": \"Markdown warning/error string\" }\n"
        "  ]\n"
        "}\n\n"
        "Analyze only the lines showing additions or changes (+ lines) in the diff. "
        "Identify the file path and line number precisely. If no issues are found, return an empty comments list.\n\n"
        f"Here is the diff to analyze:\n\n{diff_content}"
    )

    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        print("🚀 Sending diff to Gemini API for secure analysis...")
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
        
        # Extract generated text content
        text_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Parse model's JSON response to validate schema
        ai_reviews = json.loads(text_response)
        
        # Write verified JSON output back to disk
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ai_reviews, f, indent=2)
        
        print(f"✅ AI Review completed. Issues found: {len(ai_reviews.get('comments', []))}")

    except urllib.error.HTTPError as e:
        print(f"❌ API HTTP Error: {e.code} - {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during AI review processing: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
