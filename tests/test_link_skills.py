import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LINK_SCRIPT = REPO_ROOT / "scripts" / "link_skills.sh"


class LinkSkillsTest(unittest.TestCase):

    def test_custom_destination_links_docs_peer(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_dir = tmp_path / "agent" / "skills"

            result = subprocess.run(
                [str(LINK_SCRIPT), "--dest", f"test={skills_dir}"],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (skills_dir / "benchmark-efficiency").resolve(),
                REPO_ROOT / "skills" / "benchmark-efficiency",
            )
            self.assertEqual((tmp_path / "agent" / "docs").resolve(), REPO_ROOT / "docs")
            self.assertTrue(
                (
                    skills_dir
                    / "benchmark-efficiency"
                    / "../../docs/conventions/machines.md"
                ).exists()
            )


if __name__ == "__main__":
    unittest.main()
