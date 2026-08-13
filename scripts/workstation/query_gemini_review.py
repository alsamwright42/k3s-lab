#!/usr/bin/env python3
import os
import sys
import json
import argparse
import urllib.request
import urllib.error
import time
import random
import re

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract Git diff and consult Gemini for secure homelab code review annotations."
    )
    parser.add_argument(
        "--diff-path",
        default=os.environ.get("GEMINI_DIFF_PATH", "pr_changes.diff"),
        help="Path to the input Git diff file"
    )
    parser.add_argument(
        "--output-path",
        default=os.environ.get("GEMINI_OUTPUT_PATH", "review_output.json"),
        help="Path to save the generated JSON review findings"
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        help="The Gemini model name to query"
    )
    parser.add_argument(
        "--api-version",
        default=os.environ.get("GEMINI_API_VERSION", "v1beta"),
        help="The Gemini API version to use"
    )
    return parser.parse_args()

def parse_diff_to_changes_list(diff_content):
    """
    Parses a unified diff and returns a formatted list of files and absolute line numbers
    indicating where lines of code were added or modified (+ lines).
    This serves as a high-density index for the LLM to map comments precisely.
    """
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    current_file = None
    lines_by_file = {}
    
    current_line = 0
    for line in diff_content.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            lines_by_file[current_file] = []
        elif line.startswith("@@"):
            match = hunk_re.match(line)
            if match:
                current_line = int(match.group(1))
        elif current_file and current_line > 0:
            if line.startswith("+") and not line.startswith("+++"):
                lines_by_file[current_file].append((current_line, line[1:]))
                current_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                # Deleted lines do not advance line numbers in the new file
                pass
            else:
                # Unchanged context lines advance the line count
                current_line += 1
                
    # Format into a clean text block
    formatted_list = []
    for filename, lines in lines_by_file.items():
        if lines:
            formatted_list.append(f"=== FILE: {filename} ===")
            for line_num, content in lines:
                formatted_list.append(f"Line {line_num}: {content}")
            formatted_list.append("") # Spacer
            
    return "\n".join(formatted_list)

def filter_suppressed_comments(review_data, repo_root="."):
    """
    Filters out any comments pointing to lines in files that contain '# ai-ignore'
    or standard comment line equivalent 'ai-ignore' overrides.
    """
    comments = review_data.get("comments", [])
    filtered_comments = []
    
    for comment in comments:
        filename = comment.get("file")
        line_num = comment.get("line")
        
        if not filename or not line_num:
            filtered_comments.append(comment)
            continue
            
        file_path = os.path.join(repo_root, filename)
        if not os.path.exists(file_path):
            filtered_comments.append(comment)
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            idx = int(line_num) - 1
            if 0 <= idx < len(lines):
                target_line = lines[idx]
                if "ai-ignore" in target_line:
                    print(f"離 Suppressed AI comment on {filename}:{line_num} due to inline 'ai-ignore' override.")
                    continue
        except Exception as e:
            print(f"⚠️ Warning reading file {filename} during suppression check: {e}", file=sys.stderr)
            
        filtered_comments.append(comment)
        
    review_data["comments"] = filtered_comments
    return review_data

def sanitize_json_response(text):
    """
    Safely strips any surrounding markdown code block markers (like ```json ... ```)
    returned by the LLM before passing it to the json parser.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text

def main():
    args = parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    diff_path = args.diff_path
    output_path = args.output_path
    model = args.model
    api_version = args.api_version

    # Initialize default empty comments file to ensure downstream steps don't crash
    default_output = {"comments": []}
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    except Exception:
        pass

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

    # Extract exact lines of code modified with their line numbers
    changes_list = parse_diff_to_changes_list(diff_content)
    if not changes_list:
        print("✅ No code additions or changes found in diff to analyze.")
        return

    prompt = (
        "You are an expert DevOps and Platform Engineer auditing code quality, syntax, "
        "security, and architectural anti-patterns in a Kubernetes homelab. Focus on:\n"
        "1. POSIX-safe shell scripting (avoiding bash-isms like '&>' in standard /bin/sh recipes).\n"
        "2. Safe environment sourcing and dynamic configurations in Makefiles.\n"
        "3. Terraform module declarations, ensuring required arguments are populated and secrets are sensitive.\n"
        "4. Kubernetes manifest security (avoiding hardcoded secrets or privileged contexts).\n\n"
        "Identify issues and classify them strictly as:\n"
        "- 'CRITICAL': Security vulnerabilities, credential leaks, or fatal syntax errors.\n"
        "- 'WARNING': Architectural style drift, optimizations, or style issues.\n\n"
        "You must return your output strictly in JSON format. Do not wrap your response in markdown code blocks. "
        "The JSON structure must match this exact schema:\n"
        "{\n"
        "  \"comments\": [\n"
        "    {\n"
        "      \"file\": \"filename\",\n"
        "      \"line\": line_number_integer,\n"
        "      \"severity\": \"CRITICAL or WARNING\",\n"
        "      \"message\": \"Markdown warning/error string\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Analyze only the lines showing additions or changes in this PR. "
        "You MUST map each comment 'file' and 'line' to the exact lines listed below. "
        "Do not comment on any file or line number that is not listed below. If no issues are found, return an empty comments list.\n\n"
        f"Here are the exact added/changed files and line numbers in this PR:\n\n{changes_list}\n\n"
        f"For larger context, here is the full unified diff of the changes:\n\n{diff_content}"
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

    max_retries = 5
    initial_delay = 2.0
    backoff_factor = 2.0

    for attempt in range(max_retries):
        try:
            print(f"🚀 Sending diff from '{diff_path}' to Gemini API ({api_version}/{model}) for secure analysis (Attempt {attempt + 1}/{max_retries})...")
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
            
            text_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Sanitize LLM formatting failures before parsing
            sanitized_response = sanitize_json_response(text_response)
            ai_reviews = json.loads(sanitized_response)
            
            # Apply dynamic inline suppression logic
            ai_reviews = filter_suppressed_comments(ai_reviews)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(ai_reviews, f, indent=2)
            
            print(f"✅ AI Review completed. Issues found: {len(ai_reviews.get('comments', []))}. Saved results to '{output_path}'.")
            break

        except urllib.error.HTTPError as e:
            if e.code in [429, 503] and attempt < max_retries - 1:
                sleep_time = initial_delay * (backoff_factor ** attempt) + random.uniform(0.1, 1.0)
                print(f"⚠️ Gemini API returned transient error HTTP {e.code} ({e.reason}). Retrying in {sleep_time:.2f}s...", file=sys.stderr)
                time.sleep(sleep_time)
                continue
            else:
                print(f"❌ API HTTP Error: {e.code} - {e.read().decode('utf-8')}", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error during AI review processing: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
