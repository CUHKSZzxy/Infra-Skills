from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
README = REPO_ROOT / "README.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> dict[str, object]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.DOTALL)
    if match is None:
        raise ValueError("missing YAML frontmatter delimited by ---")
    try:
        values = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(values, dict):
        raise ValueError("YAML frontmatter must be a mapping")
    return values


class SkillDocsTest(unittest.TestCase):

    def test_frontmatter_rejects_malformed_or_incomplete_headers(self):
        samples = {
            "missing opener": "name: example\n---\n",
            "missing closer": "---\nname: example\ndescription: Use when testing\n",
            "invalid closer": "---\nname: example\n---extra\n",
            "malformed YAML": "---\nname: example\ndescription: Use when tasks: fail\n---\n",
            "list": "---\n- example\n---\n",
            "scalar": "---\nexample\n---\n",
            "empty": "---\n\n---\n",
        }
        for label, text in samples.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                parse_frontmatter(text)

    def test_frontmatter_supports_yaml_strings_and_metadata(self):
        text = (
            "---\n"
            'name: "example"\n'
            "description: >-\n"
            "  Use when checking\n"
            "  skill metadata.\n"
            "metadata:\n"
            "  short-description: Example skill\n"
            "---\n"
            "# Example\n"
        )
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=newline):
                fields = parse_frontmatter(text.replace("\n", newline))
                self.assertEqual(fields["name"], "example")
                self.assertEqual(fields["description"], "Use when checking skill metadata.")
                self.assertEqual(fields["metadata"], {"short-description": "Example skill"})

    def test_skill_frontmatter_matches_directory_and_trigger_style(self):
        skill_docs = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
        self.assertTrue(skill_docs, "no skill docs found")

        for path in skill_docs:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                frontmatter = parse_frontmatter(read_text(path))
                skill_name = path.parent.name
                self.assertEqual(frontmatter.get("name"), skill_name)
                self.assertRegex(skill_name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                self.assertLessEqual(len(skill_name), 64)
                description = frontmatter.get("description", "")
                self.assertIsInstance(description, str)
                self.assertLessEqual(len(description), 1024)
                self.assertTrue(
                    description.startswith("Use when "),
                    f"{skill_name} description should be trigger-first",
                )

    def test_readme_skill_index_matches_skill_directories(self):
        readme = read_text(README)
        readme_skills = set(re.findall(r"\| `/([^`]+)` \|", readme))
        disk_skills = {path.parent.name for path in SKILLS_ROOT.glob("*/SKILL.md")}

        self.assertEqual(readme_skills, disk_skills)

    def test_relative_markdown_links_resolve(self):
        markdown_paths = [
            README,
            *REPO_ROOT.glob("docs/**/*.md"),
            *SKILLS_ROOT.glob("**/*.md"),
        ]
        for path in markdown_paths:
            # Examples in fenced blocks are not document navigation links.
            prose = re.sub(r"(?ms)^```.*?^```[^\n]*$", "", read_text(path))
            targets = re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", prose)
            for target in targets:
                if ":" in target or target.startswith("#"):
                    continue
                with self.subTest(path=path.relative_to(REPO_ROOT), target=target):
                    destination = path.parent / target.split("#", 1)[0]
                    self.assertTrue(destination.exists(), f"broken link: {target}")


if __name__ == "__main__":
    unittest.main()
