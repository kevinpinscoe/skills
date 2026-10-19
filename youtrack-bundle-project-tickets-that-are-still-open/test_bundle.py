#!/usr/bin/env python3
"""Offline tests for bundle.py (AI-94).

No YouTrack, no yt-export and no gather are run: the API, the exporter and gather are all
replaced with fakes, and output goes to a temporary directory instead of ~/tmp.

Run from this directory:  python3 -m unittest -v test_bundle
"""

import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import bundle  # noqa: E402

STATUS_VALUES = [{"name": n, "isResolved": n == "Done"} for n in
                 ("To do", "In Progress", "Done", "BLOCKED", "Not yet started", "Wont do")]
PROJECTS = [{"id": "0-50", "shortName": "POE", "name": "PCT or POE Tooling"},
            {"id": "0-39", "shortName": "AI", "name": "AI projects"},
            {"id": "0-7", "shortName": "POEX", "name": "Something Else"}]


def status_field(name):
    return {"name": "Status", "value": {"name": name} if name else None,
            "projectCustomField": {"field": {"id": "157-2"}}}


def list_issue(issue_id, status, project="POE", summary=None):
    return {"idReadable": issue_id, "summary": summary or f"{issue_id} title",
            "project": {"shortName": project}, "customFields": [status_field(status)]}


def dep(issue, role="depends_on", status="Open", project=None, label=None):
    project = project or issue.split("-")[0]
    return {"role": role, "blocking": role in ("depends_on", "blocks"), "label": label or role,
            "direction": "INWARD", "link_type": {"id": "169-1", "name": "Depend"},
            "issue": issue, "summary": f"{issue} title", "project": project,
            "same_project": project == "POE", "status": status,
            "terminal": status in ("Done", "Wont do")}


def export_md(issue_id, relationships=(), description="Body", comments="", inaccessible=()):
    meta = {"schema": "yt-export.dependency-metadata/1", "issue": issue_id,
            "relationships": list(relationships), "inaccessible_links": list(inaccessible),
            "relationships_complete": not inaccessible, "remaining_effort_minutes": None}
    return textwrap.dedent(f"""\
        # {issue_id} — title

        ## Description

        {description}

        ## Links

        _No linked issues._

        ## Dependency Metadata

        ```json
        """) + json.dumps(meta, indent=2) + "\n```\n\n## Comments\n\n" + (comments or "_No comments._") + "\n"


class FakeApi:
    def __init__(self, issues, projects=PROJECTS, values=STATUS_VALUES):
        self.issues, self.projects, self.values = issues, projects, values
        self.calls = []

    def __call__(self, path, params=None):
        params = params or {}
        self.calls.append((path, dict(params)))
        if path == "admin/projects":
            return self.page(self.projects, params)
        if path.endswith("/customFields"):
            return [{"id": "186-1", "field": {"id": "157-0"}}, {"id": "186-2", "field": {"id": "157-2"}}]
        if path.endswith("/customFields/186-2"):
            return {"bundle": {"values": self.values}}
        if path == "issues":
            return self.page(self.issues, params)
        raise AssertionError(f"unexpected path {path}")

    @staticmethod
    def page(rows, params):
        skip, top = int(params.get("$skip", 0)), int(params.get("$top", len(rows)))
        return rows[skip:skip + top]


FAKE_GATHER = textwrap.dedent("""\
    import sys, os
    args = sys.argv[1:]
    d = args[args.index("--dir") + 1]; name = args[args.index("--output") + 1]
    files = [args[i + 1] for i, a in enumerate(args) if a == "--file"]
    out = os.path.join(os.environ["FAKE_GATHER_OUT"], name)
    if os.path.exists(out) and "--overwrite" not in args:
        sys.exit(1)
    with open(out, "w") as fh:
        fh.write("# " + args[args.index("--title") + 1] + "\\n")
        for f in files:
            fh.write("\\n## " + os.path.join(d, f) + "\\n\\n````markdown\\n" + open(os.path.join(d, f)).read() + "````\\n")
    print(out)
""")


class Harness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        gather = self.out / "fake-gather"
        gather.write_text(f"#!{sys.executable}\n" + FAKE_GATHER)
        gather.chmod(0o755)
        self.gather = str(gather)
        patches = [mock.patch.object(bundle, "OUTPUT_DIR", self.out),
                   mock.patch.dict(os.environ, {"FAKE_GATHER_OUT": str(self.out)})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def run_build(self, issues, exports, project="POE", overwrite=False, failing=()):
        def exporter(issue_id, path):
            if issue_id in failing:
                return False, "yt-export: HTTP 403"
            path.write_text(exports.get(issue_id) or export_md(issue_id), encoding="utf-8")
            return True, ""
        args = SimpleNamespace(project=project, overwrite=overwrite, keep_exports=False)
        api = FakeApi(issues)
        with mock.patch("sys.stdout"):
            path, code = bundle.build(args, api, exporter=exporter, gather_bin=self.gather)
        return path, code, path.read_text(encoding="utf-8"), api


class ProjectAndStatus(unittest.TestCase):
    def test_resolve_by_short_or_full_name(self):
        self.assertEqual(bundle.resolve_project(PROJECTS, "poe")["id"], "0-50")
        self.assertEqual(bundle.resolve_project(PROJECTS, "pct or poe tooling")["id"], "0-50")

    def test_unknown_project_never_guessed(self):
        with self.assertRaisesRegex(bundle.BundleError, "Close matches: POE"):
            bundle.resolve_project(PROJECTS, "PO")
        with self.assertRaises(bundle.BundleError):
            bundle.resolve_project(PROJECTS, "")

    def test_terminal_spellings_checked_live(self):
        bundle.check_terminal_spellings(STATUS_VALUES)
        renamed = [v for v in STATUS_VALUES if v["name"] != "Wont do"] + [{"name": "Won't do"}]
        with self.assertRaisesRegex(bundle.BundleError, "'Wont do'"):
            bundle.check_terminal_spellings(renamed)


class Selection(unittest.TestCase):
    def test_excludes_exactly_done_and_wont_do(self):
        issues = [list_issue("POE-1", "Done"), list_issue("POE-2", "Wont do"),
                  list_issue("POE-3", "In Progress"), list_issue("POE-4", "BLOCKED"),
                  list_issue("POE-5", None), list_issue("POE-6", "done"),
                  list_issue("AI-9", "To do", project="AI")]
        selected, counts, foreign = bundle.select_open(issues, "POE")
        self.assertEqual([i["idReadable"] for i in selected], ["POE-3", "POE-4", "POE-5", "POE-6"])
        self.assertEqual(counts["Done"], 1)
        self.assertEqual(counts["(no Status)"], 1)
        self.assertEqual(foreign, ["AI-9"])

    def test_selection_does_not_use_resolution(self):
        # A Done issue that YouTrack never resolved (the pre-POE-56 Category veto) is still excluded.
        done_unresolved = list_issue("POE-1", "Done")
        done_unresolved["resolved"] = None
        self.assertEqual(bundle.select_open([done_unresolved], "POE")[0], [])

    def test_order_is_numeric(self):
        issues = [list_issue(f"POE-{n}", "To do") for n in (10, 2, 1)]
        self.assertEqual([i["idReadable"] for i in bundle.select_open(issues, "POE")[0]],
                         ["POE-1", "POE-2", "POE-10"])


class Pagination(unittest.TestCase):
    def test_every_page_read(self):
        rows = [list_issue(f"POE-{n}", "To do") for n in range(1, 2 * bundle.PAGE_SIZE + 6)]
        api = FakeApi(rows)
        got = bundle.get_all(api, "issues", "f", {"query": "project: {POE}"})
        self.assertEqual(len(got), len(rows))
        self.assertEqual([c[1]["$skip"] for c in api.calls], [0, bundle.PAGE_SIZE, 2 * bundle.PAGE_SIZE])

    def test_exact_page_multiple_reads_one_empty_page(self):
        rows = [list_issue(f"POE-{n}", "To do") for n in range(1, bundle.PAGE_SIZE + 1)]
        api = FakeApi(rows)
        self.assertEqual(len(bundle.get_all(api, "issues", "f")), bundle.PAGE_SIZE)
        self.assertEqual(len(api.calls), 2)


class SafeName(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(bundle.safe_name("PCT or POE Tooling", "POE"), "PCT-or-POE-Tooling")
        self.assertEqual(bundle.safe_name("../etc/passwd", "X"), "etc-passwd")
        self.assertEqual(bundle.safe_name("KFED - Host config & management", "KHC"),
                         "KFED-Host-config-management")
        self.assertEqual(bundle.safe_name("ÜÜÜ", "KHC"), "KHC")
        self.assertEqual(bundle.safe_name("a" * 300, "A"), "a" * 100)
        for name in ("a/b", "a\\b", "a\nb", ".hidden", "x:y*z?"):
            result = bundle.safe_name(name, "S")
            self.assertRegex(result, r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class Analysis(unittest.TestCase):
    def entries(self, exports):
        return [{"id": i, "parsed": bundle.parse_export(md)} for i, md in exports.items()]

    def test_working_order_parallel_and_cross_project(self):
        a = self.entries({
            "POE-1": export_md("POE-1"),
            "POE-2": export_md("POE-2", [dep("POE-1"), dep("KHC-9", status="Done", project="KHC")]),
            "POE-3": export_md("POE-3", [dep("POE-1")]),
            "POE-4": export_md("POE-4", [dep("POE-2"), dep("POE-3")]),
            "POE-5": export_md("POE-5", [dep("WMI-2", status="In Progress", project="WMI")]),
        })
        result = bundle.analyse(a)
        self.assertEqual(result["can_start"], ["POE-1"])
        self.assertEqual(result["layers"], [["POE-1", "POE-5"], ["POE-2", "POE-3"], ["POE-4"]])
        self.assertEqual([d["issue"] for d in result["rows"]["POE-5"]["outside_open"]], ["WMI-2"])
        self.assertEqual([d["issue"] for d in result["rows"]["POE-2"]["done"]], ["KHC-9"])
        self.assertEqual([d["issue"] for d in result["rows"]["POE-2"]["cross_project"]], ["KHC-9"])
        self.assertEqual(result["cycles"], [])

    def test_cycle_detected_and_not_ordered(self):
        result = bundle.analyse(self.entries({
            "POE-1": export_md("POE-1", [dep("POE-2")]),
            "POE-2": export_md("POE-2", [dep("POE-1")]),
            "POE-3": export_md("POE-3"),
        }))
        self.assertEqual(result["cycles"], [["POE-1", "POE-2"]])
        self.assertEqual(result["layers"], [["POE-3"]])
        self.assertEqual(result["blocked_by_cycle"], ["POE-1", "POE-2"])

    def test_inaccessible_links_block_can_start(self):
        result = bundle.analyse(self.entries({"POE-1": export_md(
            "POE-1", inaccessible=[{"count": 1, "label": "depends on", "role": "depends_on"}])}))
        self.assertEqual(result["can_start"], [])

    def test_informational_links_are_not_dependencies(self):
        result = bundle.analyse(self.entries({"POE-1": export_md("POE-1", [
            dep("POE-7", role="parent"), dep("POE-8", role="related"),
            dep("POE-9", role="duplicates", label="duplicates")])}))
        self.assertEqual(result["can_start"], ["POE-1"])
        self.assertEqual(result["rows"]["POE-1"]["in_set_open"], [])
        self.assertEqual(result["relations"]["parent"], [("POE-1", "subtask of POE-7")])

    def test_related_pair_listed_once(self):
        result = bundle.analyse(self.entries({
            "POE-1": export_md("POE-1", [dep("POE-2", role="related")]),
            "POE-2": export_md("POE-2", [dep("POE-1", role="related")])}))
        self.assertEqual(result["relations"]["related"], [("POE-1", "POE-2")])

    def test_text_candidates_are_separate_from_links(self):
        entry = {"id": "POE-1", "parsed": bundle.parse_export(export_md(
            "POE-1", [dep("POE-2")],
            description="Blocked by POE-3 until AI-61 merges.",
            comments="### Comment 1\n\nSee POE-2 and POE-1. Waiting on KHC-4."))}
        cand = bundle.text_candidates(entry)
        self.assertEqual(cand["mentions"], ["AI-61", "KHC-4", "POE-3"])
        self.assertEqual(cand["phrases"], ["Blocked by POE-3 until AI-61 merges.",
                                           "See POE-2 and POE-1. Waiting on KHC-4."])


class EndToEnd(Harness):
    def test_bundle_preserves_every_export_unmodified(self):
        exports = {
            "POE-2": export_md("POE-2", [dep("POE-3"), dep("KHC-9", status="Done", project="KHC")],
                               comments="### Comment 1 — 7-1\n\nfull ```text``` kept"),
            "POE-3": export_md("POE-3"),
        }
        issues = [list_issue("POE-1", "Done"), list_issue("POE-2", "In Progress"),
                  list_issue("POE-3", "Not yet started"), list_issue("POE-4", "Wont do")]
        path, code, text, api = self.run_build(issues, exports)
        self.assertEqual(code, 0)
        self.assertEqual(path.name, "gather-youtrack-project-PCT-or-POE-Tooling.md")
        for md in exports.values():
            self.assertIn(md, text)
        self.assertIn("- **Project:** PCT or POE Tooling", text)
        self.assertIn("- **Short name:** POE", text)
        self.assertIn("- **Included issues:** 2", text)
        self.assertIn("| 1 | POE-2 |", text)
        self.assertIn("| 2 | POE-3 |", text)
        self.assertNotIn("| POE-1 |", text)
        self.assertIn("- POE-2 depends on POE-3", text)
        self.assertIn("- POE-2: KHC-9 is Done", text)
        self.assertIn("not a critical path", text)
        self.assertLess(text.index("## Dependency overview"), text.index("## Missing data and limitations"))
        self.assertTrue(any(c[0] == "issues" and c[1]["query"] == "project: {POE}" for c in api.calls))
        leftovers = [p for p in self.out.iterdir() if p.name.endswith(tuple("_")) or "-exports-" in p.name]
        self.assertEqual(leftovers, [])

    def test_empty_project(self):
        path, code, text, _ = self.run_build([list_issue("POE-1", "Done")], {})
        self.assertEqual(code, 0)
        self.assertIn("- **Included issues:** 0", text)
        self.assertIn("_No open issues: every issue in this project is `Done` or `Wont do`._", text)

    def test_existing_bundle_not_overwritten_without_flag(self):
        target = self.out / "gather-youtrack-project-PCT-or-POE-Tooling.md"
        target.write_text("keep me")
        with self.assertRaisesRegex(bundle.BundleError, "already exists"):
            self.run_build([list_issue("POE-2", "To do")], {})
        self.assertEqual(target.read_text(), "keep me")
        _, code, text, _ = self.run_build([list_issue("POE-2", "To do")], {}, overwrite=True)
        self.assertEqual(code, 0)
        self.assertIn("POE-2", text)

    def test_export_failure_is_reported_not_hidden(self):
        _, code, text, _ = self.run_build(
            [list_issue("POE-2", "To do"), list_issue("POE-3", "To do")], {}, failing={"POE-3"})
        self.assertEqual(code, 3)
        self.assertIn("**INCOMPLETE:** 1 selected issue(s) could not be exported", text)
        self.assertIn("**POE-3 was not exported**", text)

    def test_api_read_needs_brokered_config(self):
        with mock.patch.dict(os.environ, {"YOUTRACK_CURL_CONFIG": ""}):
            with self.assertRaisesRegex(bundle.BundleError, "parzival exec --as ai youtrack-claude-code"):
                bundle.curl_fetcher("http://127.0.0.1:9")


if __name__ == "__main__":
    unittest.main()
