from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
README = REPO_ROOT / "README.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    frontmatter = text.split("---\n", 2)[1]
    values: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


class SkillDocsTest(unittest.TestCase):

    def test_skill_frontmatter_matches_directory_and_trigger_style(self):
        skill_docs = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
        self.assertTrue(skill_docs, "no skill docs found")

        for path in skill_docs:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                frontmatter = parse_frontmatter(read_text(path))
                skill_name = path.parent.name
                self.assertEqual(frontmatter.get("name"), skill_name)
                description = frontmatter.get("description", "")
                self.assertTrue(
                    description.startswith("Use when "),
                    f"{skill_name} description should be trigger-first",
                )

    def test_readme_skill_index_matches_skill_directories(self):
        readme = read_text(README)
        readme_skills = set(re.findall(r"\| `/([^`]+)` \|", readme))
        disk_skills = {path.parent.name for path in SKILLS_ROOT.glob("*/SKILL.md")}

        self.assertEqual(readme_skills, disk_skills)

    def test_new_skill_guidance_points_to_specific_conventions(self):
        session_skill = read_text(
            SKILLS_ROOT / "update-session-skill" / "SKILL.md"
        )
        normalized = " ".join(session_skill.split())

        self.assertIn("docs/conventions/machines.md", session_skill)
        self.assertIn("docs/conventions/environments.md", session_skill)
        self.assertIn("docs/conventions/linking.md", session_skill)
        self.assertIn(
            "Prefer updating an existing file over adding a new skill",
            normalized,
        )

    def test_conventions_are_split_without_old_local_convention_doc(self):
        old_doc = "local-" "conventions.md"
        self.assertFalse((REPO_ROOT / "docs" / old_doc).exists())

        convention_docs = {
            path.name for path in (REPO_ROOT / "docs" / "conventions").glob("*.md")
        }
        self.assertEqual(
            convention_docs,
            {
                "benchmark-artifacts.md",
                "deployment-context.md",
                "environments.md",
                "linking.md",
                "machines.md",
            },
        )

        markdown_paths = [
            README,
            *REPO_ROOT.glob("docs/**/*.md"),
            *SKILLS_ROOT.glob("**/*.md"),
        ]
        for path in markdown_paths:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertNotIn(old_doc, read_text(path))


if __name__ == "__main__":
    unittest.main()
