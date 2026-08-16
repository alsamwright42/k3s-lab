import os
import shutil
import subprocess
import tempfile
import unittest
from builtins import FileNotFoundError
from pathlib import Path

class TestMakefileClean(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Read the standard CI environment toggle
        is_ci = os.environ.get("CI", "false").lower() == "true"
        make_installed = shutil.which("make") is not None

        if not make_installed:
            if is_ci:
                # 🛑 Hard Fail in CI: Prevent silent test suppression
                raise RuntimeError(
                    "❌ ERROR: 'make' utility is missing in the CI runner environment! "
                    "Makefile unit tests cannot be verified and must not be skipped."
                )
            else:
                # 🟡 Graceful Skip on local workstations
                raise unittest.SkipTest(
                    "⚠️  Skipping Makefile tests: 'make' utility not found on this workstation."
                )


    def setUp(self):
        # 1. Create a temporary directory for isolated testing
        self.test_dir = Path(tempfile.mkdtemp(prefix="makefile-clean-test-"))
        
        # 2. Locate the Makefile in the repository root
        current_file = Path(__file__).resolve()
        
        self.makefile_src = None
        for parent in current_file.parents:
            candidate = parent / "Makefile"
            if candidate.exists():
                self.makefile_src = candidate
                break
                
        # Fallback for the sandbox environment to locate our synced artifact
        if not self.makefile_src:
            sandbox_candidate = Path("/workspace/artifacts/Makefile")
            if sandbox_candidate.exists():
                self.makefile_src = sandbox_candidate

        if not self.makefile_src:
            raise FileNotFoundError("Could not locate the project Makefile to test.")
            
        # Copy the actual Makefile to our temporary directory
        shutil.copy2(self.makefile_src, self.test_dir / "Makefile")
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def write_test_harness(self, test_path):
        # We append a test-only target that calls our internal Makefile functions directly
        test_content = f"""
# Disable profile evaluations during unit testing        
USE_PROFILES := false

include Makefile

test-secure-tmp-macro:
	@echo "RESULT: $(if $(call is_secure_tmp_safe,{test_path}),SAFE,UNSAFE)"

test-build-dir-macro:
	@echo "RESULT: $(if $(call is_build_dir_safe,{test_path}),SAFE,UNSAFE)"
"""
        (self.test_dir / "Makefile.test").write_text(test_content, encoding="utf-8")


    # =========================================================================
    # 🔎 DIRECT NATIVE MAKE-LEVEL MACRO TESTS
    # =========================================================================

    def test_makefile_secure_tmp_safe_macro_directly(self):
        """Verify that the Makefile's is_secure_tmp_safe macro evaluates correctly."""
        safe_cases = ["/tmp/k3s-lab-1000", "/tmp/test-folder", "/tmp/a"]
        unsafe_cases = ["/", "", "/tmp", "/tmp/", "/home/sysop", "relative-folder", "../outside"]

        for path in safe_cases:
            self.write_test_harness(path)
            result = subprocess.run(
                ["make", "-f", "Makefile.test", "test-secure-tmp-macro"],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("RESULT: SAFE", result.stdout, f"Expected path '{path}' to evaluate as SAFE, but got: {result.stdout}")

        for path in unsafe_cases:
            self.write_test_harness(path)
            result = subprocess.run(
                ["make", "-f", "Makefile.test", "test-secure-tmp-macro"],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("RESULT: UNSAFE", result.stdout, f"Expected path '{path}' to evaluate as UNSAFE, but got: {result.stdout}")

    def test_makefile_build_dir_safe_macro_directly(self):
        """Verify that the Makefile's is_build_dir_safe macro evaluates correctly."""
        # Relative safe cases
        safe_relative = ["build", "build/sub", "bin-output"]
        for path in safe_relative:
            self.write_test_harness(path)
            result = subprocess.run(
                ["make", "-f", "Makefile.test", "test-build-dir-macro"],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("RESULT: SAFE", result.stdout, f"Expected path '{path}' to evaluate as SAFE, but got: {result.stdout}")

        # Absolute safe cases (must be subpaths of self.test_dir, which is $(CURDIR) during test run)
        safe_absolute = [
            str(self.test_dir / "build"),
            str(self.test_dir / "build/sub"),
            str(self.test_dir / "custom-output")
        ]
        for path in safe_absolute:
            self.write_test_harness(path)
            result = subprocess.run(
                ["make", "-f", "Makefile.test", "test-build-dir-macro"],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("RESULT: SAFE", result.stdout, f"Expected absolute path '{path}' under project root to evaluate as SAFE, but got: {result.stdout}")

        # Unsafe cases
        unsafe_cases = [
            "/", "/home", "~", "~/projects", "../outside", "..", ".", "", 
            "build/../../etc",
            str(self.test_dir), # project root itself is unsafe
            f"{self.test_dir}/", # project root with trailing slash is unsafe
            str(self.test_dir.parent), # parent is unsafe
            f"{self.test_dir}/../outside" # escape via traversal
        ]
        for path in unsafe_cases:
            self.write_test_harness(path)
            result = subprocess.run(
                ["make", "-f", "Makefile.test", "test-build-dir-macro"],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("RESULT: UNSAFE", result.stdout, f"Expected path '{path}' to evaluate as UNSAFE, but got: {result.stdout}")

    # =========================================================================
    # 💥 OPERATIONAL CLEAN TARGET INTEGRATION TESTS (Using overrides)
    # =========================================================================

    def test_live_secure_tmp_safe_deletion(self):
        """Test that running 'make clean' with a valid SECURE_TMP_DIR under /tmp deletes it physically."""
        secure_tmp = tempfile.mkdtemp(prefix="k3s-lab-test-safe-")
        try:
            dummy_file = Path(secure_tmp) / "kustomize-argocd.yaml"
            dummy_file.write_text("apiVersion: v1", encoding="utf-8")
            
            result = subprocess.run(
                ["make", "clean", f"SECURE_TMP_DIR={secure_tmp}", "BUILD_DIR=dummy-nonexistent", "USE_PROFILES=false"],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0, f"Make clean failed: {result.stderr}")
            self.assertIn("✅ Purged secure temp directory:", result.stdout)
            self.assertFalse(os.path.exists(secure_tmp))
        finally:
            if os.path.exists(secure_tmp):
                shutil.rmtree(secure_tmp)

    def test_live_secure_tmp_unsafe_skipped(self):
        """Test that running 'make clean' with an unsafe SECURE_TMP_DIR is safely skipped without crashing."""
        unsafe_paths = ["/", "/tmp", "/tmp/", "/var/tmp", "build", "../escape"]
        for path in unsafe_paths:
            result = subprocess.run(
                ["make", "clean", f"SECURE_TMP_DIR={path}", "BUILD_DIR=dummy-nonexistent", "USE_PROFILES=false"],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("⚠️ Skipped SECURE_TMP_DIR purge:", result.stdout)

    def test_live_build_dir_safe_deletion(self):
        """Test that running 'make clean' with a valid relative BUILD_DIR deletes it."""
        build_dir = "test-build-relative-folder-xyz"
        target_path = self.test_dir / build_dir
        target_path.mkdir(parents=True, exist_ok=True)
        (target_path / "rendered.yaml").write_text("dummy", encoding="utf-8")
        
        result = subprocess.run(
            ["make", "clean", "SECURE_TMP_DIR=dummy-secure-nonexistent", f"BUILD_DIR={build_dir}", "USE_PROFILES=false"],
            cwd=self.test_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Make clean failed: {result.stderr}")
        self.assertIn(f"✅ Purged local build directory:", result.stdout)
        self.assertFalse(target_path.exists())

    def test_live_build_dir_unsafe_skipped(self):
        """Test that running 'make clean' with an unsafe BUILD_DIR is safely skipped without crashing."""
        unsafe_paths = ["/", "/home", "~", "build/../../etc", "..", ".", ""]
        for path in unsafe_paths:
            result = subprocess.run(
                ["make", "clean", "SECURE_TMP_DIR=dummy-secure-nonexistent", f"BUILD_DIR={path}", "USE_PROFILES=false"],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("⚠️ Skipped BUILD_DIR purge:", result.stdout)

    # def test_live_secure_tmp_safe_deletion(self):
    #     """Test that running 'make clean' with a valid SECURE_TMP_DIR under /tmp deletes it."""
    #     # Create a mock folder directly under /tmp using system tools
    #     secure_tmp = tempfile.mkdtemp(prefix="k3s-lab-test-safe-")
    #     try:
    #         # Seed it with dynamic files
    #         dummy_file = Path(secure_tmp) / "kustomize-argocd.yaml"
    #         dummy_file.write_text("apiVersion: v1\nkind: Namespace", encoding="utf-8")
            
    #         # Execute clean with overriden paths
    #         result = subprocess.run(
    #             ["make", "clean", "USE_PROFILES=false", f"SECURE_TMP_DIR={secure_tmp}", "BUILD_DIR=dummy-build-nonexistent"],
    #             cwd=self.test_dir,
    #             capture_output=True,
    #             text=True
    #         )
    #         self.assertEqual(result.returncode, 0)
    #         self.assertIn(f"✅ Purged secure temp directory: {secure_tmp}", result.stdout)
            
    #         # Verify actual deletion has occurred on host disk
    #         self.assertFalse(os.path.exists(secure_tmp))
    #     finally:
    #         # Cleanup in case the execution test failed
    #         if os.path.exists(secure_tmp):
    #             shutil.rmtree(secure_tmp)

    # def test_live_secure_tmp_unsafe_skipped(self):
    #     """Test that running 'make clean' with dangerous absolute/relative SECURE_TMP_DIR is blocked."""
    #     unsafe_paths = ["/", "/tmp", "/tmp/", "/var/tmp", "build", "../escape"]
    #     for path in unsafe_paths:
    #         result = subprocess.run(
    #             ["make", "clean", "USE_PROFILES=false", f"SECURE_TMP_DIR={path}", "BUILD_DIR=dummy-build-nonexistent"],
    #             cwd=self.test_dir,
    #             capture_output=True,
    #             text=True
    #         )
    #         self.assertEqual(result.returncode, 0)
    #         self.assertIn("⚠️ Skipped SECURE_TMP_DIR purge:", result.stdout)

    # def test_live_build_dir_safe_deletion(self):
    #     """Test that running 'make clean' with a valid relative BUILD_DIR deletes it."""
    #     # Provision build folder locally inside our temp dir
    #     build_dir = "test-build-relative-folder-xyz"
    #     target_path = self.test_dir / build_dir
    #     target_path.mkdir(parents=True, exist_ok=True)
    #     (target_path / "rendered.yaml").write_text("dummy", encoding="utf-8")
        
    #     # Execute clean overriding BUILD_DIR
    #     result = subprocess.run(
    #         ["make", "clean", "USE_PROFILES=false", "SECURE_TMP_DIR=dummy-secure-nonexistent", f"BUILD_DIR={build_dir}"],
    #         cwd=self.test_dir,
    #         capture_output=True,
    #         text=True
    #     )
    #     self.assertEqual(result.returncode, 0)
    #     self.assertIn(f"✅ Purged local build directory: {build_dir}", result.stdout)
        
    #     # Verify physical deletion
    #     self.assertFalse(target_path.exists())

    # def test_live_build_dir_unsafe_skipped(self):
    #     """Test that running 'make clean' with dangerous/absolute BUILD_DIR paths is blocked."""
    #     unsafe_paths = ["/", "/home", "~", "build/../../etc", "..", ".", ""]
    #     for path in unsafe_paths:
    #         result = subprocess.run(
    #             ["make", "clean", "USE_PROFILES=false", "SECURE_TMP_DIR=dummy-secure-nonexistent", f"BUILD_DIR={path}"],
    #             cwd=self.test_dir,
    #             capture_output=True,
    #             text=True
    #         )
    #         self.assertEqual(result.returncode, 0)
    #         self.assertIn("⚠️ Skipped BUILD_DIR purge:", result.stdout)


if __name__ == "__main__":
    unittest.main()
