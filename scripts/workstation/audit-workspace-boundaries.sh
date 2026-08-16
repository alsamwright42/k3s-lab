#!/bin/sh
# githooks/pre-commit.d/05-enforce-workspace-boundaries
# Ensures transient staging manifests or flat-files do not pollute the repo index.

set -eu

# Retrieve all staged files (Added, Copied, Modified)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo "✅ No staged files to audit."
    exit 0
fi

FAILED=0

for FILE in $STAGED_FILES; do
    # Enforce strict boundary controls on Kubernetes Manifests (.yaml / .yml)
    case "$FILE" in
        *.yaml|*.yml)
            # Skip workflow files or other expected system files
            case "$FILE" in
                .github/workflows/*)
                    continue
                    ;;
            esac

            # Check for root-level manifest leakage (e.g. kustomize-argocd.yaml in root)
            if [ "$(dirname "$FILE")" = "." ]; then
                echo "❌ ERROR: Manifest file leaked in repository root: '$FILE'"
                echo "   All staging manifests must be compiled into the SECURE_TMP_DIR (/tmp) via 'make'."
                FAILED=1
                continue
            fi

            # ADR_002 Check: Prohibit flat-filing directly inside manifests/, base/, or apps/
            DIR_NAME=$(dirname "$FILE")
            case "$DIR_NAME" in
                manifests)
                    echo "❌ ERROR: Prohibited flat-file manifest detected: '$FILE'"
                    echo "   ADR 002 mandates that all manifests be structured inside dedicated subfolders."
                    FAILED=1
                    ;;
                manifests/base)
                    echo "❌ ERROR: Prohibited flat-file inside base/: '$FILE'"
                    echo "   Move this file into a dedicated subfolder (e.g. manifests/base/argocd/manifest.yaml)."
                    FAILED=1
                    ;;
                manifests/apps)
                    echo "❌ ERROR: Prohibited flat-file inside apps/: '$FILE'"
                    echo "   Move this file into a dedicated subfolder (e.g. manifests/apps/portainer/manifest.yaml)."
                    FAILED=1
                    ;;
            esac
            ;;
    esac
done

if [ "$FAILED" -eq 1 ]; then
    echo "🛑 Boundary Audit Failed! Please resolve the errors above before committing."
    exit 1
fi

echo "✅ All staged files comply with repository boundary standards."
exit 0
