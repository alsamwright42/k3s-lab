import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestBundleCodebase(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(tempfile.mkdtemp(prefix="bundle-codebase-test-"))
        self.script_src = Path(__file__).resolve().parents[1] / "scripts" / "workstation" / "bundle-codebase.sh"
        self.script_dst = self.repo_root / "scripts" / "workstation" / "bundle-codebase.sh"
        self.script_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.script_src, self.script_dst)
        self.script_dst.chmod(0o755)

        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo_root, check=True, stdout=subprocess.DEVNULL)
        # Prevent test suite from crashing in headless CI/CD runners lacking Git configs
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo_root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_root, check=True)

    def tearDown(self):
        shutil.rmtree(self.repo_root)

    def write_file(self, path: Path, content: str, stage: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if stage:
            subprocess.run(["git", "add", str(path.relative_to(self.repo_root))], cwd=self.repo_root, check=True, stdout=subprocess.DEVNULL)

    def run_bundler(self, env: dict | None = None) -> subprocess.CompletedProcess:
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        return subprocess.run(
            ["bash", str(self.script_dst)],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            env=process_env,
        )

    def test_bundle_includes_tracked_files(self):
        self.write_file(self.repo_root / "Makefile", "# Makefile\n")
        self.write_file(self.repo_root / "local-profile.env", "ENV=local\n")
        self.write_file(self.repo_root / "scripts" / "workstation" / "helper.sh", "echo hello\n")
        self.write_file(self.repo_root / "manifests" / "app.yaml", "kind: ConfigMap\n")
        self.write_file(self.repo_root / "core" / "k3s-config" / "k3s.service", "[Service]\nExecStart=/usr/local/bin/k3s\n")
        self.write_file(self.repo_root / "inventory" / "hosts.ini", "[all]\n")
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.repo_root, check=True, stdout=subprocess.DEVNULL)

        result = self.run_bundler()
        self.assertEqual(result.returncode, 0, f"Bundler failed: {result.stderr}")

        output_file = self.repo_root / "docs" / "planning" / "active-codebase.md"
        self.assertTrue(output_file.exists())

        output = output_file.read_text(encoding="utf-8")
        self.assertIn("# 📂 Active Codebase State", output)
        self.assertIn("Last compiled:", output)
        self.assertIn("This file provides high-density context of tracked configurations for AI alignment.", output)
        self.assertIn("## 🛠️ Core Automation Files", output)
        self.assertIn("### 📄 File: Makefile", output)
        self.assertIn("```text\n# Makefile\n```", output)
        self.assertIn("### 📄 File: local-profile.env", output)
        self.assertIn("```text\nENV=local\n```", output)
        self.assertIn("## 🐚 Active Shell Scripts", output)
        self.assertIn("### 📄 File: scripts/workstation/helper.sh", output)
        self.assertIn("```bash\necho hello\n```", output)
        self.assertIn("## ☸️ Declarative Kubernetes Manifests", output)
        self.assertIn("### 📄 File: manifests/app.yaml", output)
        self.assertIn("```yaml\nkind: ConfigMap\n```", output)
        self.assertIn("### 📄 File: core/k3s-config/k3s.service", output)
        self.assertIn("### 📄 File: inventory/hosts.ini", output)

    def test_bundle_excludes_untracked_files(self):
        self.write_file(self.repo_root / "Makefile", "# Makefile\n")
        self.write_file(self.repo_root / "scripts" / "workstation" / "helper.sh", "echo hello\n")
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.repo_root, check=True, stdout=subprocess.DEVNULL)

        untracked_path = self.repo_root / "manifests" / "untracked.yaml"
        untracked_path.parent.mkdir(parents=True, exist_ok=True)
        untracked_path.write_text("kind: ConfigMap\n", encoding="utf-8")

        result = self.run_bundler()
        self.assertEqual(result.returncode, 0, f"Bundler failed: {result.stderr}")

        output_file = self.repo_root / "docs" / "planning" / "active-codebase.md"
        self.assertTrue(output_file.exists())

        output = output_file.read_text(encoding="utf-8")
        self.assertNotIn("untracked.yaml", output)
        self.assertNotIn("kind: ConfigMap", output)

    def test_bundle_allows_output_override(self):
        self.write_file(self.repo_root / "Makefile", "# Makefile\n")
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.repo_root, check=True, stdout=subprocess.DEVNULL)

        override_path = self.repo_root / "tmp-output.md"
        result = self.run_bundler({"OUTPUT_FILE": str(override_path)})
        self.assertEqual(result.returncode, 0, f"Bundler failed: {result.stderr}")

        self.assertTrue(override_path.exists())
        self.assertIn("# 📂 Active Codebase State", override_path.read_text(encoding="utf-8"))

    def test_auto_creates_missing_output_directories(self):
        self.write_file(self.repo_root / "local-profile.env", "ENV=local\n")
        output_path = self.repo_root / "brand-new-path" / "subfolder" / "compiled-code.md"

        result = self.run_bundler({"OUTPUT_FILE": str(output_path)})
        self.assertEqual(result.returncode, 0, f"Bundler failed: {result.stderr}")
        self.assertTrue(output_path.exists())
        self.assertIn("# 📂 Active Codebase State", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
