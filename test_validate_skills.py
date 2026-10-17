#!/usr/bin/env python3
"""Offline tests for validate_skills.py. Every case builds its own temporary
repository; nothing outside it is read or written.

Run: python3 test_validate_skills.py
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate_skills as vs  # noqa: E402

GOOD = """---
name: {name}
category: {category}
description: Does one thing.
disable-model-invocation: true
---

# A Skill

> Does one thing.

## Prerequisites

- none

## Parameters

| Name | Description | Default |
|------|-------------|---------|

## Instructions

1. **Do it.**

## Success Criteria

- It is done.

## Notes

- None.
"""


class Repo:
    """A throwaway repository root holding skill directories."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="validate-skills-")

    def skill(self, name, text=None, run_sh=True, executable=True, category=None):
        d = os.path.join(self.root, name)
        os.makedirs(d, exist_ok=True)
        if text is not False:
            category = category or name.split("-")[0]
            with open(os.path.join(d, "SKILL.md"), "w") as fh:
                fh.write(text if text is not None else GOOD.format(name=name, category=category))
        if run_sh:
            p = os.path.join(d, "run.sh")
            with open(p, "w") as fh:
                fh.write("#!/usr/bin/env bash\n")
            os.chmod(p, 0o755 if executable else 0o644)
        return d

    def problems(self, name):
        return vs.check_skill(self.root, name)

    def run(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vs.main(["--root", self.root])
        return code, out.getvalue()


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(shutil.rmtree, self.repo.root)

    def assertProblem(self, name, fragment):
        problems = self.repo.problems(name)
        self.assertTrue(any(fragment in p for p in problems), f"{fragment!r} not in {problems}")

    def test_compliant_skill_passes(self):
        self.repo.skill("food-make-tea")
        self.assertEqual(self.repo.problems("food-make-tea"), [])
        code, out = self.repo.run()
        self.assertEqual(code, 0)
        self.assertIn("1 of 1 owned skills comply", out)

    def test_multi_hyphen_category(self):
        self.repo.skill("raspberry-pi-5-reboot", category="raspberry-pi-5")
        self.assertEqual(self.repo.problems("raspberry-pi-5-reboot"), [])

    def test_additional_sections_anywhere_are_allowed(self):
        text = GOOD.format(name="food-make-tea", category="food")
        text = text.replace("## Prerequisites", "## Scope\n\nOnly tea.\n\n## Prerequisites")
        text = text.replace("## Instructions", "## Unattended invocation\n\nNo questions.\n\n## Instructions")
        text = text.replace("## Success Criteria", "## Guardrails\n\nNone.\n\n## Success Criteria")
        self.repo.skill("food-make-tea", text)
        self.assertEqual(self.repo.problems("food-make-tea"), [])

    def test_optional_sections_may_be_absent(self):
        text = GOOD.format(name="food-make-tea", category="food")
        text = text.split("## Parameters")[0] + "## Instructions" + text.split("## Instructions")[1]
        text = text.split("## Notes")[0]
        self.repo.skill("food-make-tea", text)
        self.assertEqual(self.repo.problems("food-make-tea"), [])

    def test_missing_run_sh(self):
        self.repo.skill("food-make-tea", run_sh=False)
        self.assertProblem("food-make-tea", "missing run.sh")

    def test_run_sh_not_executable(self):
        self.repo.skill("food-make-tea", executable=False)
        self.assertProblem("food-make-tea", "run.sh is not executable")

    def test_missing_skill_md(self):
        self.repo.skill("food-make-tea", text=False)
        self.assertProblem("food-make-tea", "missing SKILL.md")

    def test_directory_with_neither_file_fails(self):
        os.makedirs(os.path.join(self.repo.root, "food-empty"))
        code, out = self.repo.run()
        self.assertEqual(code, 1)
        self.assertIn("FAIL food-empty", out)

    def test_no_frontmatter(self):
        self.repo.skill("food-make-tea", "# A Skill\n\n> x\n")
        self.assertProblem("food-make-tea", "no YAML frontmatter")

    def test_missing_frontmatter_keys_and_flag(self):
        text = GOOD.format(name="food-make-tea", category="food")
        text = text.replace("description: Does one thing.\n", "").replace("disable-model-invocation: true\n", "")
        self.repo.skill("food-make-tea", text)
        self.assertProblem("food-make-tea", "missing description:")
        self.assertProblem("food-make-tea", "disable-model-invocation: true is missing")

    def test_flag_must_be_true(self):
        text = GOOD.format(name="food-make-tea", category="food").replace(
            "disable-model-invocation: true", "disable-model-invocation: false")
        self.repo.skill("food-make-tea", text)
        self.assertProblem("food-make-tea", "disable-model-invocation: true is missing")

    def test_name_must_equal_directory(self):
        self.repo.skill("food-make-tea", GOOD.format(name="food-make-coffee", category="food"))
        self.assertProblem("food-make-tea", "does not equal the directory name")

    def test_category_must_be_a_slug(self):
        self.repo.skill("food-make-tea", GOOD.format(name="food-make-tea", category="Food"))
        self.assertProblem("food-make-tea", "not a lowercase hyphenated slug")

    def test_category_must_prefix_directory(self):
        self.repo.skill("food-make-tea", GOOD.format(name="food-make-tea", category="drink"))
        self.assertProblem("food-make-tea", "not the directory-name prefix")

    def test_missing_h1(self):
        text = GOOD.format(name="food-make-tea", category="food").replace("# A Skill\n", "")
        self.repo.skill("food-make-tea", text)
        self.assertProblem("food-make-tea", "not an H1 title")

    def test_missing_blockquote(self):
        text = GOOD.format(name="food-make-tea", category="food").replace("> Does one thing.\n", "")
        self.repo.skill("food-make-tea", text)
        self.assertProblem("food-make-tea", "no > blockquote")

    def test_missing_required_section(self):
        text = GOOD.format(name="food-make-tea", category="food").replace("## Success Criteria", "## Done when")
        self.repo.skill("food-make-tea", text)
        self.assertProblem("food-make-tea", "missing ## Success Criteria")

    def test_required_sections_out_of_order(self):
        text = GOOD.format(name="food-make-tea", category="food")
        text = text.replace("## Prerequisites", "## TMP").replace("## Instructions", "## Prerequisites") \
                   .replace("## TMP", "## Instructions")
        self.repo.skill("food-make-tea", text)
        self.assertProblem("food-make-tea", "out of order")

    def test_headings_in_code_fences_do_not_count(self):
        text = GOOD.format(name="food-make-tea", category="food").replace(
            "1. **Do it.**", "1. **Do it.**\n\n````markdown\n## Notes\n```\n## Prerequisites\n```\n````\n")
        self.repo.skill("food-make-tea", text)
        self.assertEqual(self.repo.problems("food-make-tea"), [])
        hidden = GOOD.format(name="food-make-tea", category="food").replace(
            "## Instructions", "~~~\n## Instructions\n~~~")
        self.repo.skill("food-make-tea", hidden)
        self.assertProblem("food-make-tea", "missing ## Instructions")

    def test_excluded_directories_are_skipped(self):
        for name in ("synced", "ai-wt", "gsd-plan", ".git-ish"):
            os.makedirs(os.path.join(self.repo.root, name))
        self.repo.skill("food-make-tea")
        code, out = self.repo.run()
        self.assertEqual(code, 0)
        self.assertIn("Owned skills (1)", out)

    def test_gitignored_directories_are_skipped(self):
        if shutil.which("git") is None:
            self.skipTest("git not installed")
        subprocess.run(["git", "init", "-q", self.repo.root], check=True)
        with open(os.path.join(self.repo.root, ".gitignore"), "w") as fh:
            fh.write("scratch-dir/\n")
        os.makedirs(os.path.join(self.repo.root, "scratch-dir"))
        self.repo.skill("food-make-tea")
        code, out = self.repo.run()
        self.assertEqual(code, 0)
        self.assertNotIn("scratch-dir", out)

    def test_linked_skills_are_reported_and_never_fail(self):
        other = tempfile.mkdtemp(prefix="other-repo-")
        self.addCleanup(shutil.rmtree, other)
        target = os.path.join(other, "jira-make-ticket")
        os.makedirs(target)
        with open(os.path.join(target, "SKILL.md"), "w") as fh:
            fh.write("---\nname: jira-make-ticket\n---\n\n# No blockquote\n")  # no flag, no sections
        os.symlink(target, os.path.join(self.repo.root, "jira-make-ticket"))
        os.symlink("../nowhere/jira-gone", os.path.join(self.repo.root, "jira-gone"))
        self.repo.skill("food-make-tea")
        code, out = self.repo.run()
        self.assertEqual(code, 0)
        self.assertIn("Owned skills (1)", out)
        self.assertIn("Linked skills (2)", out)
        self.assertIn("jira-make-ticket", out)
        self.assertIn("no frontmatter flag", out)
        self.assertIn("jira-gone -> ../nowhere/jira-gone: does not resolve here", out)

    def test_one_failure_makes_the_run_fail(self):
        self.repo.skill("food-make-tea")
        self.repo.skill("food-make-toast", executable=False)
        code, out = self.repo.run()
        self.assertEqual(code, 1)
        self.assertIn("1 of 2 owned skills comply", out)

    def test_validator_writes_nothing(self):
        self.repo.skill("food-make-tea")
        self.repo.skill("food-make-toast", run_sh=False)

        def snapshot():
            state = {}
            for dirpath, dirnames, filenames in os.walk(self.repo.root):
                for n in dirnames + filenames:
                    p = os.path.join(dirpath, n)
                    st = os.lstat(p)
                    state[p] = (st.st_mode, st.st_size, st.st_mtime_ns)
            return state

        before = snapshot()
        self.repo.run()
        self.assertEqual(before, snapshot())

    def test_missing_root_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(vs.main(["--root", os.path.join(self.repo.root, "absent")]), 2)


if __name__ == "__main__":
    unittest.main()
