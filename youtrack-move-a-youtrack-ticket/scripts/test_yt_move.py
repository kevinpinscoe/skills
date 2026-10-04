#!/usr/bin/env python3
"""Offline tests for yt_move.py. Fixtures only: no API call, no move.

The regression case is the KSA-81 -> GLASS-2 move of 2026-10-04, where
YouTrack rewrote the bare old key inside comment text, including branch names,
worktree paths and commit subjects. fixtures/ksa81-before.json and
fixtures/glass2-after.json are synthetic text modelled on that behaviour.

Run: python3 test_yt_move.py
"""

import copy
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import yt_move  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as fh:
        return json.load(fh)


def comment(snap, cid):
    return next(c for c in snap["comments"] if c["id"] == cid)


class RegressionKsa81(unittest.TestCase):
    """The observed move: structure intact, text rewritten, some of it wrongly."""

    def setUp(self):
        self.before = fixture("ksa81-before.json")
        self.after = fixture("glass2-after.json")

    def report(self, after=None):
        return yt_move.compare(self.before, after or self.after)

    def test_observed_move_is_structural_pass_needing_remediation(self):
        rep = self.report()
        self.assertEqual(rep["immutable_id"], "PASS")
        self.assertEqual(rep["structural"], [])
        self.assertEqual(rep["unexplained"], [])
        self.assertEqual(rep["reference_rewrites"], 3)
        self.assertEqual(len(rep["artifact_rewrites"]), 6)
        self.assertEqual(rep["left_as_written"], 4)
        self.assertEqual(rep["other_issues"], 1)
        self.assertEqual(yt_move.verdicts(rep), ("PASS", "NEEDS REMEDIATION", 3))

    def test_artifact_reasons(self):
        reasons = sorted(a["reason"] for a in self.report()["artifact_rewrites"])
        self.assertEqual(reasons, sorted([
            "branch, worktree or command", "path or ref range", "commit subject",
            "suffixed name or filename", "inline code", "branch, worktree or command"]))

    def test_render_never_says_plain_pass_for_text(self):
        out = yt_move.render(self.report())
        self.assertIn("Structural preservation: PASS", out)
        self.assertIn("Historical-artifact rewrites: 6", out)
        self.assertIn("Text preservation: NEEDS REMEDIATION", out)
        self.assertNotIn("Text preservation: PASS", out)

    def test_reference_only_rewrite_is_clean(self):
        before = copy.deepcopy(self.before)
        after = copy.deepcopy(self.after)
        keep = {"7-101", "7-106"}
        for snap in (before, after):
            snap["comments"] = [c for c in snap["comments"] if c["id"] in keep]
            snap["referencing_issues"] = []
        rep = yt_move.compare(before, after)
        self.assertEqual(yt_move.verdicts(rep), ("PASS", "CLEAN", 0))
        self.assertEqual(rep["reference_rewrites"], 2)  # comment 7-101 + description

    def test_extra_edit_is_unexplained(self):
        after = copy.deepcopy(self.after)
        comment(after, "7-101")["text"] += " Also fixed a typo."
        rep = self.report(after)
        self.assertEqual(len(rep["unexplained"]), 1)
        self.assertEqual(yt_move.verdicts(rep)[2], 1)

    def test_recreated_comment_fails_structurally(self):
        after = copy.deepcopy(self.after)
        comment(after, "7-103")["id"] = "7-999"
        rep = self.report(after)
        self.assertTrue(any("missing" in p for p in rep["structural"]))
        self.assertEqual(yt_move.verdicts(rep)[0], "FAIL")

    def test_author_or_created_change_fails(self):
        for key, value in (("author", {"login": "admin"}), ("created", 1)):
            after = copy.deepcopy(self.after)
            comment(after, "7-101")[key] = value
            self.assertTrue(self.report(after)["structural"], key)

    def test_comment_updated_time(self):
        after = copy.deepcopy(self.after)
        comment(after, "7-101")["updated"] = 5   # its text was rewritten: a note
        self.assertEqual(self.report(after)["structural"], [])
        after = copy.deepcopy(self.after)
        comment(after, "7-106")["updated"] = 5   # text unchanged: structural
        self.assertTrue(self.report(after)["structural"])

    def test_custom_field_rules(self):
        after = copy.deepcopy(self.after)
        after["customFields"][0]["value"] = {"name": "Open"}
        self.assertTrue(any("'Status' changed" in p for p in self.report(after)["structural"]))
        after = copy.deepcopy(self.after)
        after["customFields"] = after["customFields"][:-1]
        self.assertTrue(any("'Spent time' lost" in p for p in self.report(after)["structural"]))
        after = copy.deepcopy(self.after)
        after["customFields"][1]["value"] = "GLASS-2"   # Working branch rewritten
        rep = self.report(after)
        self.assertEqual(rep["structural"], [])
        self.assertIn("artifact field", [a["reason"] for a in rep["artifact_rewrites"]])

    def test_entity_id_and_links(self):
        after = copy.deepcopy(self.after); after["id"] = "3-1"
        self.assertEqual(self.report(after)["immutable_id"], "FAIL")
        after = copy.deepcopy(self.after); after["links"][0]["issues"] = []
        self.assertIn("links differ", self.report(after)["structural"])

    def test_unclassified_other_issue_needs_remediation(self):
        before = copy.deepcopy(self.before)
        after = copy.deepcopy(self.after)
        for snap in (before, after):
            snap["comments"] = [c for c in snap["comments"] if c["id"] == "7-101"]
            snap["referencing_issues"] = []
        after["unclassified_referencing_issues"] = [{"id": "3-5", "idReadable": "KHC-65"}]
        self.assertEqual(yt_move.verdicts(yt_move.compare(before, after))[1], "NEEDS REMEDIATION")

    def test_risk_prediction_matches_observed_outcome(self):
        rows = yt_move.risk(self.before, "KSA-81")
        likely = [r for r in rows if r["likely_rewritten"]]
        rep = self.report()
        self.assertEqual(len(likely), rep["reference_rewrites"] + len(rep["artifact_rewrites"]))
        self.assertEqual(len(rows) - len(likely), rep["left_as_written"])


class ExitSemantics(unittest.TestCase):
    """0 clean; 3 structurally clean but artifacts to remediate; 1 stop."""

    def run_cli(self, before, after):
        with tempfile.TemporaryDirectory() as d:
            b, a = os.path.join(d, "b.json"), os.path.join(d, "a.json")
            for path, data in ((b, before), (a, after)):
                with open(path, "w") as fh:
                    json.dump(data, fh)
            with open(os.devnull, "w") as null:
                saved, sys.stdout = sys.stdout, null
                try:
                    return yt_move.main(["compare", b, a])
                finally:
                    sys.stdout = saved

    def setUp(self):
        self.before = fixture("ksa81-before.json")
        self.after = fixture("glass2-after.json")

    def test_exit_3_artifacts_detected(self):
        self.assertEqual(self.run_cli(self.before, self.after), 3)

    def test_exit_0_clean(self):
        before, after = copy.deepcopy(self.before), copy.deepcopy(self.after)
        for snap in (before, after):
            snap["comments"] = [c for c in snap["comments"] if c["id"] == "7-101"]
            snap["referencing_issues"] = []
        self.assertEqual(self.run_cli(before, after), 0)

    def test_exit_1_unexplained_or_structural(self):
        after = copy.deepcopy(self.after)
        comment(after, "7-101")["text"] = "rewritten by hand"
        self.assertEqual(self.run_cli(self.before, after), 1)
        after = copy.deepcopy(self.after)
        after["comments"].pop()
        self.assertEqual(self.run_cli(self.before, after), 1)


class CoverageClaim(unittest.TestCase):
    CLAIM = "searched all issues visible to the Claude_Code identity to exhaustion"

    def test_claim_in_report_and_followup(self):
        rep = yt_move.compare(fixture("ksa81-before.json"), fixture("glass2-after.json"))
        out = yt_move.render(rep)
        self.assertIn("\nCross-issue scan: " + self.CLAIM + "\n", out)
        self.assertNotIn("all issues in YouTrack", out)
        self.assertIn(self.CLAIM, yt_move.followup_text("KSA-81", "GLASS-2", rep))

    def test_no_claim_without_scan(self):
        before = fixture("ksa81-before.json"); del before["_scan"]
        out = yt_move.render(yt_move.compare(before, fixture("glass2-after.json")))
        self.assertIn("Cross-issue scan: not run", out)

    def test_part_a_requires_human_review_of_artifact_hits(self):
        text = yt_move.followup_text("KTA-19", "GLASS-2")
        self.assertIn("**Required:** before changing a Markdown hit that looks like a branch name", text)


class WalkTests(unittest.TestCase):
    def test_occurrences_skip_longer_numbers(self):
        self.assertEqual(yt_move.find_occurrences("KSA-81 KSA-810 xKSA-81-a", "KSA-81"), [0, 16])

    def test_partial_rewrite(self):
        walk = yt_move.rewrite_walk("a KSA-81 b `KSA-81`", "a GLASS-2 b `KSA-81`",
                                    "KSA-81", "GLASS-2")
        self.assertEqual(walk, [(2, True), (12, False)])

    def test_other_change_is_none(self):
        self.assertIsNone(yt_move.rewrite_walk("a KSA-81", "b GLASS-2", "KSA-81", "GLASS-2"))
        self.assertIsNone(yt_move.rewrite_walk("KSA-81", "GLASS-20", "KSA-81", "GLASS-2"))
        self.assertIsNone(yt_move.rewrite_walk("KSA-810", "GLASS-20", "KSA-81", "GLASS-2"))

    def test_classify(self):
        cases = {
            "blocked by KSA-81": "reference",
            "issue KSA-81": "reference",
            "https://youtrack.kevininscoe.com/issue/KSA-81": "reference",
            "branch KSA-81": "artifact",
            "ai-wt/KSA-81": "artifact",
            "KSA-81-frodo-hostkey": "artifact",
            "git checkout KSA-81": "artifact",
            "feat(x): KSA-81 thing": "artifact",
            "path/to/KSA-81/file": "artifact",
            "stacked on KSA-81": "artifact",
            "LOCAL KSA-81 = 0937acb": "artifact",
            "no KSA-81 worktrees left": "artifact",
        }
        for text, kind in cases.items():
            i = text.index("KSA-81")
            self.assertEqual(yt_move.classify(text, i, "KSA-81")[0], kind, text)


class PagerTests(unittest.TestCase):
    def test_short_pages_do_not_end_paging(self):
        data = list(range(250))
        pages = []

        def fetch(skip, top):
            pages.append(skip)
            return data[skip:skip + min(top, 60)]   # server caps pages at 60
        self.assertEqual(yt_move.paginate(fetch), data)
        self.assertEqual(pages[-1], 250)

    def test_stalled_pager_raises(self):
        with self.assertRaises(yt_move.Fail):
            yt_move.paginate(lambda skip, top: [{"id": "same"}])


class BoundaryTests(unittest.TestCase):
    """The contract the POE ticket's rg inventory and rewrite utility share."""

    def setUp(self):
        self.rx = re.compile(yt_move.boundary_pattern("KTA-19"))

    def test_matches(self):
        for text in ("KTA-19", "(KTA-19)", ".../KTA-19", "KTA-19.", "KTA-19,",
                     "https://youtrack.kevininscoe.com/issue/KTA-19"):
            self.assertTrue(self.rx.search(text), text)

    def test_non_matches(self):
        for text in ("KTA-190", "KTA-191", "XKTA-19", "ABC-KTA-19"):
            self.assertFalse(self.rx.search(text), text)


class FollowupTests(unittest.TestCase):
    def test_without_remediation(self):
        text = yt_move.followup_text("KTA-19", "GLASS-2")
        self.assertIn("Old issue ID: KTA-19\nNew issue ID: GLASS-2", text)
        self.assertIn("(?<![A-Za-z0-9-])KTA\\-19(?![0-9])", text)
        self.assertIn("rg -n -P --glob '*.md'", text)
        self.assertIn("~/private-tools/yt-rewrite-moved-issue-id.py", text)
        self.assertIn("# Part A", text)
        self.assertNotIn("# Part B", text)
        self.assertEqual(yt_move.followup_summary("KTA-19", "GLASS-2"),
                         "Update Markdown references after KTA-19 moved to GLASS-2")

    def test_with_remediation(self):
        rep = yt_move.compare(fixture("ksa81-before.json"), fixture("glass2-after.json"))
        text = yt_move.followup_text("KSA-81", "GLASS-2", rep, "~/tmp/r.json")
        self.assertIn("# Part A", text)
        self.assertIn("# Part B", text)
        self.assertIn("Never mass-replace GLASS-2 back to KSA-81", text)
        self.assertIn("~/tmp/KSA-81-before-project-move.api.json", text)
        self.assertIn("comment 7-102", text)
        self.assertTrue(yt_move.followup_summary("KSA-81", "GLASS-2", rep)
                        .startswith("Update Markdown references and restore historical text"))


class ValidationTests(unittest.TestCase):
    def test_issue_ids(self):
        self.assertEqual(yt_move.normalise_issue_id("kta-19"), "KTA-19")
        self.assertEqual(yt_move.normalise_issue_id(
            "https://youtrack.kevininscoe.com/issue/KTA-19/some-slug"), "KTA-19")
        for bad in ("KTA", "KTA-0", "19", "KTA-19; rm -rf ~", "../KTA-19"):
            with self.assertRaises(yt_move.Fail, msg=bad):
                yt_move.normalise_issue_id(bad)

    def test_issue_ref_accepts_entity_ids(self):
        self.assertEqual(yt_move.issue_ref("3-2509"), "3-2509")
        self.assertEqual(yt_move.issue_ref("kta-19"), "KTA-19")

    def test_move_rejects_bad_ids_before_any_call(self):
        with self.assertRaises(yt_move.Fail):
            yt_move.move("KTA-19", "0-50")
        with self.assertRaises(yt_move.Fail):
            yt_move.move("3-2509", "GLASS")

    def test_api_requires_parzival_child(self):
        saved = os.environ.pop("YOUTRACK_CURL_CONFIG", None)
        try:
            with self.assertRaises(yt_move.Fail):
                yt_move.api("GET", "/api/issues/KTA-19")
        finally:
            if saved is not None:
                os.environ["YOUTRACK_CURL_CONFIG"] = saved


class RefusalTests(unittest.TestCase):
    ISSUE = {"idReadable": "DEMO-19", "project": {"id": "0-901"}}

    def project(self, **kw):
        p = {"id": "0-902", "shortName": "DEST", "name": "Demo destination",
             "searchable_issue": True}
        p.update(kw)
        return p

    def test_ordinary_destination_allowed(self):
        yt_move.refuse_destination(self.ISSUE, self.project())

    def test_refusals(self):
        for kw in ({"template": True}, {"archived": True}, {"id": "0-901"},
                   {"shortName": "TMPL"}, {"name": "Project template"},
                   {"searchable_issue": False}, {"searchable_issue": None}):
            with self.assertRaises(yt_move.Fail, msg=kw):
                yt_move.refuse_destination(self.ISSUE, self.project(**kw))


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.good = os.path.join(HERE, "fixtures", "DEMO-19-export.md")

    def test_good_export(self):
        self.assertEqual(yt_move.check_export(self.good, "DEMO-19", "Demo source"), [])

    def test_wrong_issue_or_project(self):
        self.assertTrue(yt_move.check_export(self.good, "DEMO-190"))
        self.assertTrue(yt_move.check_export(self.good, "DEMO-19", "Demo destination"))

    def test_missing_and_empty(self):
        self.assertTrue(yt_move.check_export("/nonexistent/x.md", "DEMO-19"))
        with tempfile.NamedTemporaryFile(suffix=".md") as fh:
            self.assertIn("empty", yt_move.check_export(fh.name, "DEMO-19")[0])


if __name__ == "__main__":
    unittest.main(verbosity=1)
