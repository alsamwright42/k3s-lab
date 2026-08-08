#!/usr/bin/env bash
# scripts/workstation/audit-shellcheck.sh
# Deterministically audits only the staged bytes of shell scripts in the Git index.
# Fulfills ADR_011 (Directory Anchoring) and ADR_013 (Secrets Sovereignty).

set -euo pipefail

# Force C.UTF-8 locale fallback to suppress host-side setlocale warnings
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# ADR 011 Rule 5: Directory Anchoring (Script is 2 levels deep)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if ! command -v shellcheck &> /dev/null; then
    echo "⚠️  [ShellCheck Audit] 'shellcheck' is not installed!"
    echo "   To enable syntax checks, run: sudo apt install shellcheck"
    exit 0
fi

echo "🔍 Auditing staged Shell scripts..."

failed=0
# diff-filter=ACMR gets ONLY staged additions, modifications, or renames
while IFS= read -r file; do
    [ -z "$file" ] && continue
    
    # Check the physical file on disk ONLY if it is part of the staged commit
    if [ -f "${REPO_ROOT}/${file}" ]; then
        first_line=$(head -n 1 "${REPO_ROOT}/${file}" || true)
        if [[ "$file" =~ \.sh$ ]] || [[ "$first_line" =~ ^#\!.*sh ]]; then
            echo "   -> Scanning working tree copy of staged file: $file"
            if ! shellcheck "${REPO_ROOT}/${file}"; then
                echo "❌ ShellCheck failed on: $file"
                failed=1
            fi
        fi
    fi
done < <(git -C "$REPO_ROOT" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)


if [ "$failed" -ne 0 ]; then
    echo "❌ [Audit Gate] ShellCheck validation failed! Fix warnings before committing."
    exit 1
fi

echo "✅ ShellCheck audit completed successfully!"
exit 0
