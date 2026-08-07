### ADR 011: Automation and Scripting Standards

#### Status
Active

#### Context
To prevent configuration drift, silent failures, and cross-platform execution bugs, all bash scripts and automation pipelines in this repository MUST adhere to the following enterprise DevOps standards.

#### Execution Rules
1. **No Error Swallowing:** Never use `2>/dev/null`, `-q` (quiet), or `-s` (silent) flags in deployment scripts. Commands must fail loudly to provide immediate debugging context.
2. **No In-Place File Mutilation:** Never use `sed -i` to edit or sanitize files during deployment execution, as it can truncate files to 0 bytes on failure. Line endings (CRLF) are managed globally via `.gitattributes`.
3. **Safe File Staging:** Never use inline SSH heredocs (`bash -c 'cat <<EOF'`) to write configurations directly to protected remote directories. Files must be staged via `scp` to `/tmp/` and subsequently moved using `ssh target "sudo mv /tmp/file /destination"`.
4. **Headless SSH Safety:** All `ssh` and `scp` commands executed within loops or automation scripts must include `-n -o BatchMode=yes -o ConnectTimeout=5` to prevent stdin gobbling and silent interactive prompt hangs.
5. **Directory Anchoring:** All scripts must anchor file paths dynamically to prevent Current Working Directory (CWD) execution failures. 
   *   **Mandatory Script-Level Anchoring:** Every script **must** locate its own parent folder at startup using the standard `BASH_SOURCE` stack array with an explicit index `[0]`:

       ```bash
       SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
       ```
   *   **Conditional Repository-Root Anchoring:** If (and only if) the script must resolve files, templates, or inventories located outside of its own script subdirectory, it **must** declare `REPO_ROOT` relative to its localized anchor:
        ```bash
        REPO_ROOT="$(dirname "$SCRIPT_DIR")"
        ```
   *   **Unused Variable Enforcement:** If a script does not reference files outside its parent folder, `REPO_ROOT` **must not** be defined. This eliminates dead execution context and ensures automated pre-commit audits (such as ShellCheck) pass natively without requiring redundant silencing directives.

