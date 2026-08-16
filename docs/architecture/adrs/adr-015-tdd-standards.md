### ADR 015: Test-Driven Development (TDD) Standards

#### Status
Active

#### Context
As the K3s bare-metal homelab has matured, our repository has scaled to include a complex array of shell scripts, Makefiles, Terraform plans, and Kubernetes manifests [ADR_002_Application_Directory_Structure.md, ADR_004_IaC_and_Automation_Boundaries.md, ADR_011_Automation_and_Scripting_Standards.md]. This operational density introduces significant system risks [ADR_011_Automation_and_Scripting_Standards.md]:
1. **Host-Level File Destructiveness:** Cleanup targets in our `Makefile` (such as `clean`) must evaluate dynamic variables (e.g., `SECURE_TMP_DIR` and `BUILD_DIR`) that, if evaluated as empty or malformed due to shell parsing issues, can cause catastrophic recursive directory deletions on the host workstation (`rm -rf /` or `rm -rf /home/sysop`) [ADR_006_K3s_Node_Bootstrap_and_Automation_Summary.md, ADR_011_Automation_and_Scripting_Standards.md].
2. **Repository Pollution and Drift:** Temporary files, unencrypted secrets (like `.env` profiles), and un-encapsulated flat-file Kubernetes manifests are prone to leaking out of their designated jailing directories and being committed directly into the Git repository, violating ADR 002 directory rules [ADR_002_Application_Directory_Structure.md, ADR_013_Secrets_Management_and_Sover.md].

To ensure our automated boundaries remain sound and to protect the host OS, we require a rigorous testing framework that validates our scripting logic and Makefile boundaries before commits are pushed or merged.

#### Decision
We will establish a formal **Test-Driven Development (TDD) Standards** protocol for all repository-level automation scripts, Makefile routines, pre-commit githooks, and configuration boundaries. This standard mandates the following rules:

##### 1. The Homelab IaC TDD Lifecycle Protocol
All modifications or additions of custom automation scripts, Makefile targets, and repository boundaries must strictly follow the TDD loop:
* **Phase 1 (RED):** Developers must write isolated unit tests inside the `tests/` directory asserting the expected behavior *prior* to modifying the operational code. The tests must assert both *safe/valid* inputs (expecting success) and *malformed/dangerous* inputs (expecting immediate, non-zero failures).
* **Phase 2 (RED Verification):** Run the workstation test suite via `make test` to verify that the newly written test cases fail predictably.
* **Phase 3 (GREEN):** Implement the minimum POSIX-compliant scripting or Makefile target logic required to satisfy the failing test cases.
* **Phase 4 (REFACTOR):** Optimize variables and streamline commands while ensuring line-ending normalization (.gitattributes) is maintained, running the test suite continuously to confirm regressions are locked out.

##### 2. Separation of Concerns (Implementation vs. Verification)
To eliminate pattern-matching drift, test assertions must never merely copy-paste the shell expressions written in the Makefile. Instead:
* **The Makefile owns the implementation:** It declares the active targets, variables, and private path-safety boundaries (such as the POSIX-compliant `_is_secure_tmp_safe` or `_is_build_dir_safe` case targets).
* **The Python Test Suite owns the verification:** It drives real-world integration checks by spinning up temporary mock directories on disk, triggering the `Makefile` in child subprocesses with overridden target inputs, and verifying that the actual shell execution blocks unsafe paths and cleanly deletes safe files.

##### 3. Decoupling Monolith Tests
We strictly prohibit bundling all workstation tests into a single python test suite. Testing files must be divided cleanly on an **operational target and domain basis**. For example:
* `tests/test_makefile_clean.py`: Focuses exclusively on filesystem safety, temporary folder RAM-disk jailing, and cleanup target deletion limits.
* `tests/test_makefile_audit.py`: Focuses on workstation binary auditing, plural lazy verifiers, and dependency gates.
* `tests/test_audit_shellcheck.py`: Focuses on testing the behaviour of the pre-commit githook audit-shellcheck script.

#### Consequences & Next Steps
* **Zero Host-Deletion Risks:** By asserting path validations natively through subprocesses on every testing cycle, mitigates the possibility of a malformed directory variable to execute a destructive `rm -rf` on a developer's workstation host.
* **Zero Cowboy Engineering:** No automated pipelines or custom configurations can be merged without proving compliance via a green test suite. Local hooks and pull requests will fail automatically if a script or Makefile target is introduced without test coverage.
* **Rapid Developer Feedback Loop:** Splitting tests by target domains allows developers to run fast, lightweight, target-specific checks in their IDE integrated terminals without running the entire integration pipeline, maximizing DevEx velocity.

