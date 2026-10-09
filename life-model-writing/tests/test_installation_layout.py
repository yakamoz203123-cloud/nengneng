import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SKILL_ROOT.parent


class InstallationLayoutTests(unittest.TestCase):
    def test_clean_skill_copy_is_self_contained_and_validates(self):
        required_repository_files = (
            REPOSITORY_ROOT / "README.md",
            REPOSITORY_ROOT / "LICENSE",
            REPOSITORY_ROOT / "CHANGELOG.md",
            REPOSITORY_ROOT / "CONTRIBUTING.md",
            REPOSITORY_ROOT / "requirements-dev.txt",
        )
        for path in required_repository_files:
            self.assertTrue(path.is_file(), f"missing packaging file: {path.name}")

        with tempfile.TemporaryDirectory() as temporary:
            install_root = Path(temporary) / "skills" / "life-model-writing"
            shutil.copytree(
                SKILL_ROOT,
                install_root,
                ignore=shutil.ignore_patterns("runs", "__pycache__", "*.pyc"),
            )

            for relative_path in (
                "SKILL.md",
                "references/theory-14-diffusion-thresholds-propagation.md",
                "scripts/validate_skill.py",
                "evals/rubric.json",
            ):
                self.assertTrue(
                    (install_root / relative_path).is_file(),
                    f"missing installed asset: {relative_path}",
                )
            self.assertFalse((install_root / "evals" / "runs").exists())

            result = subprocess.run(
                [
                    sys.executable,
                    str(install_root / "scripts" / "validate_skill.py"),
                    str(install_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VALIDATION=PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
