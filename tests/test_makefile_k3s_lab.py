# tests/test_makefile_k3s.py
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests.support import enforce_test_toolchain, require_binaries

class TestMakefileK3s(unittest.TestCase):

    HARD_REQUIREMENTS = ["make"]
    SOFT_REQUIREMENTS = ["kubectl", "kustomize"]

    @classmethod
    def setUpClass(cls):
        enforce_test_toolchain(cls.HARD_REQUIREMENTS)

    def setUp(self):
        # 1. Create a temporary directory for isolated testing
        self.test_dir = Path(tempfile.mkdtemp(prefix="k3s-makefile-test-"))

        # 2. Locate the parent Makefile and k3s.mk in the repository root
        current_file = Path(__file__).resolve()
        self.makefile_src = None
        self.k3s_mk_src = None

        for parent in current_file.parents:
            makefile_cand = parent / "Makefile"
            k3s_mk_cand = parent / "k3s-lab.mk"
            if makefile_cand.exists() and not self.makefile_src:
                self.makefile_src = makefile_cand
            if k3s_mk_cand.exists() and not self.k3s_mk_src:
                self.k3s_mk_src = k3s_mk_cand

        if not self.makefile_src.exists() or not self.k3s_mk_src.exists():
            raise FileNotFoundError("Could not locate parent Makefile or k3s.mk extension.")

        # 3. Copy Makefile and k3s.mk to the temp directory
        shutil.copy2(self.makefile_src, self.test_dir / "Makefile")
        shutil.copy2(self.k3s_mk_src, self.test_dir / "k3s-lab.mk")

        # 4. Provision dummy directories and files required for parse-time checks
        self.inventory_dir = self.test_dir / "inventory"
        self.inventory_dir.mkdir(parents=True, exist_ok=True)
        self.env_file = self.inventory_dir / "local.env"
        self.env_file.write_text("DOMAIN=samjam.dedyn.io\nVIP=192.168.1.53\n", encoding="utf-8")

        # Create dummy manifests directory to prevent Kustomize errors
        self.manifest_dir = self.test_dir / "manifests/base/argocd"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        (self.manifest_dir / "kustomization.yaml").write_text("resources:\n  - deployment.yaml\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    # =========================================================================
    # ⚙️ PARSE-TIME SYNTAX & VALUE BINDING TESTS
    # =========================================================================

    def test_k3s_makefile_loads_without_syntax_errors(self):
        """Verify that make parses k3s.mk and its parent Makefile cleanly."""
        result = subprocess.run(
            ["make", "help", "USE_PROFILES=false"],
            cwd=self.test_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Makefile parsing failed: {result.stderr}")
        self.assertIn("kustomize-argocd", result.stdout)

    def test_k3s_extension_appends_required_tools(self):
        """Test that k3s.mk successfully appends its binaries to OPTIONAL_TOOLS."""
        test_harness = self.test_dir / "Makefile.test"
        test_harness.write_text(
            "include Makefile\n\ntest-tools:\n\t@echo \"TOOLS: $(OPTIONAL_TOOLS)\"\n",
            encoding="utf-8"
        )
        result = subprocess.run(
            ["make", "-f", "Makefile.test", "test-tools", "USE_PROFILES=false"],
            cwd=self.test_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        # Verify both core and k3s-specific tools exist
        self.assertIn("kubectl", result.stdout)
        self.assertIn("kustomize", result.stdout)
        self.assertIn("envsubst", result.stdout)
        self.assertIn("terraform", result.stdout)
    # =========================================================================
    # 🔬 DRY-RUN RECIPE ENFORCEMENT TESTS
    # =========================================================================

    @require_binaries("kubectl", "kustomize")
    def test_kustomize_argocd_recipe_substitutes_vars(self):
        """Verify kustomize-argocd dry-run uses correct Awk filter logic and envsubst."""
        result = subprocess.run(
            ["make", "kustomize-argocd", "-n", "USE_PROFILES=false"],
            cwd=self.test_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Dry-run failed: {result.stderr}")
        # Ensure the pipeline checks local.env key extraction
        self.assertIn("awk", result.stdout)
        self.assertIn("envsubst", result.stdout)
        self.assertIn("manifests/base/argocd/", result.stdout)

    # =========================================================================
    # 🧼 MODULAR CLEANUP INTEGRATION TESTS
    # =========================================================================

    def test_modular_clean_removes_k3s_stage_files(self):
        """Test that make clean successfully executes parent AND child cleanup blocks."""
        # 1. Manually create stage files in our mock staging directory
        secure_tmp = self.test_dir / "secure-staging"
        secure_tmp.mkdir(parents=True, exist_ok=True)

        stage_file = secure_tmp / "kustomize-argocd.yaml"
        stage_file.write_text("apiVersion: v1", encoding="utf-8")

        # 2. Run clean, targeting our mock secure directory
        result = subprocess.run(
            [
                "make", "clean",
                f"SECURE_TMP_DIR={secure_tmp}",
                "BUILD_DIR=dummy-nonexistent",
                "USE_PROFILES=false"
            ],
            cwd=self.test_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Clean target failed: {result.stderr}")

        # Ensure parent-level clean logged success
        self.assertIn("Wiping workspace build artifacts and secure caches...", result.stdout)

        # Verify files are deleted physically
        self.assertFalse(stage_file.exists(), "K3s build stage file was not deleted!")

if __name__ == "__main__":
    unittest.main()
