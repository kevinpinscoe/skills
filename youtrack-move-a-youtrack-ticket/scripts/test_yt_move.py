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
import subprocess
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


class UrlRewrites(unittest.TestCase):
    """`/issue/OLD` URLs go either way on a move: KSA-81 reported them left as
    written (not recheckable); KSA-101 -> GLASS-25 (2026-10-09) rewrote them,
    confirmed by snapshot. Synthetic text, with the KSA-81 fixtures' IDs."""

    URL = "https://youtrack.kevininscoe.com/issue/"
    TEXTS = {
        "prose": "see {u}{k} for the plan",
        "fenced": "Log:\n```\ncurl {u}{k}\n```",
        "inline": "run `open {u}{k}` now",
        "tilde": "Log:\n~~~\ncurl {u}{k}\n~~~\nThat was the log.",
        "double_tick": "run ``open `{u}{k}` `` now",
    }
    CODE_REASONS = {"fenced": "code block", "inline": "inline code",
                    "tilde": "code block", "double_tick": "inline code"}

    def setUp(self):
        # A moved issue with no text of its own, as KSA-101 had, so only the
        # referencing issue's comment decides the result.
        self.before = fixture("ksa81-before.json")
        self.after = fixture("glass2-after.json")
        for snap in (self.before, self.after):
            snap["comments"] = []
            snap["description"] = ""
        # What remains is the moved issue's artifact string fields, left as written.
        self.base_left = self.pair("nothing here", "nothing here")["left_as_written"]

    def ref_rows(self):
        return [r for r in yt_move.risk(self.before, "KSA-81") if r["issue"] != "KSA-81"]

    def pair(self, before_text, after_text):
        self.before["referencing_issues"][0]["comments"][0]["text"] = before_text
        self.after["referencing_issues"][0]["comments"][0]["text"] = after_text
        return yt_move.compare(self.before, self.after)

    def text(self, form, key):
        return self.TEXTS[form].format(u=self.URL, k=key)

    def test_baseline_has_no_mentions(self):
        rep = self.pair("nothing here", "nothing here")
        self.assertEqual(rep["reference_rewrites"], 0)
        self.assertEqual(rep["artifact_rewrites"], [])
        self.assertEqual(self.ref_rows(), [])
        self.assertEqual(yt_move.verdicts(rep), ("PASS", "CLEAN", 0))

    def test_ksa101_regression(self):
        before = f"It is tracked in KSA-81 ({self.URL}KSA-81)."
        after = f"It is tracked in GLASS-2 ({self.URL}GLASS-2)."
        self.before["referencing_issues"][0]["comments"][0]["text"] = before
        self.assertEqual([r["likely_rewritten"] for r in self.ref_rows()], [True, None])
        rep = self.pair(before, after)
        self.assertEqual(rep["reference_rewrites"], 2)
        self.assertEqual(rep["artifact_rewrites"], [])
        self.assertEqual(rep["unexplained"], [])
        self.assertEqual(rep["left_as_written"], self.base_left)
        self.assertEqual(yt_move.verdicts(rep), ("PASS", "CLEAN", 0))

    def test_url_left_as_written_in_every_form(self):
        for form in self.TEXTS:
            with self.subTest(form=form):
                t = self.text(form, "KSA-81")
                rep = self.pair(t, t)
                self.assertEqual(rep["left_as_written"], self.base_left + 1)
                self.assertEqual(rep["reference_rewrites"], 0)
                self.assertEqual(rep["artifact_rewrites"], [])  # no Part B review
                self.assertEqual(rep["unexplained"], [])
                self.assertEqual(yt_move.verdicts(rep), ("PASS", "CLEAN", 0))

    def test_url_rewritten_in_prose_is_a_reference(self):
        rep = self.pair(self.text("prose", "KSA-81"), self.text("prose", "GLASS-2"))
        self.assertEqual(rep["reference_rewrites"], 1)
        self.assertEqual(rep["artifact_rewrites"], [])
        self.assertEqual(yt_move.verdicts(rep), ("PASS", "CLEAN", 0))

    def test_url_rewritten_in_code_goes_to_part_b(self):
        for form, reason in self.CODE_REASONS.items():
            with self.subTest(form=form):
                rep = self.pair(self.text(form, "KSA-81"), self.text(form, "GLASS-2"))
                self.assertEqual(rep["reference_rewrites"], 0)
                self.assertEqual([a["reason"] for a in rep["artifact_rewrites"]], [reason])
                self.assertEqual(rep["unexplained"], [])
                self.assertEqual(yt_move.verdicts(rep), ("PASS", "NEEDS REMEDIATION", 3))
                part_b = yt_move.followup_text("KSA-81", "GLASS-2", rep)
                self.assertIn("# Part B", part_b)
                self.assertIn(f"({reason})", part_b)

    def test_code_classification_does_not_leak_into_prose(self):
        # Each code form, closed, then an issue URL in prose on a later line or
        # after the closing delimiter: both rewritten, one kind B, one kind A.
        tail = {"fenced": "\nSee {u}{k} too.", "tilde": "\nSee {u}{k} too.",
                "inline": " and {u}{k} too.", "double_tick": " and {u}{k} too."}
        for form, reason in self.CODE_REASONS.items():
            with self.subTest(form=form):
                t = self.TEXTS[form] + tail[form]
                rep = self.pair(t.format(u=self.URL, k="KSA-81"), t.format(u=self.URL, k="GLASS-2"))
                self.assertEqual(rep["reference_rewrites"], 1)
                self.assertEqual([a["reason"] for a in rep["artifact_rewrites"]], [reason])
                self.assertEqual(rep["unexplained"], [])
                self.assertEqual(yt_move.verdicts(rep)[2], 3)

    def test_unrelated_change_beside_a_code_url_is_unexplained(self):
        t = self.TEXTS["tilde"]
        rep = self.pair(t.format(u=self.URL, k="KSA-81"),
                        t.format(u=self.URL, k="GLASS-2").replace("curl", "wget"))
        self.assertEqual(len(rep["unexplained"]), 1)
        self.assertEqual(yt_move.verdicts(rep)[2], 1)

    def test_unrelated_change_beside_a_url_is_unexplained(self):
        rep = self.pair(self.text("prose", "KSA-81"),
                        self.text("prose", "GLASS-2").replace("the plan", "a plan"))
        self.assertEqual(len(rep["unexplained"]), 1)
        self.assertEqual(yt_move.verdicts(rep)[2], 1)

    def test_risk_puts_every_url_form_in_the_uncertain_bucket(self):
        for form in self.TEXTS:
            with self.subTest(form=form):
                t = self.text(form, "KSA-81")
                self.assertIsNone(yt_move.likely_rewritten(t, t.index("KSA-81"), "KSA-81"))

    def test_print_risk_buckets_add_up(self):
        import contextlib, io
        before = self.before
        before["referencing_issues"][0]["comments"][0]["text"] = (
            f"tracked in KSA-81 ({self.URL}KSA-81) and `{self.URL}KSA-81`")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            yt_move.print_risk(before)
        text = out.getvalue()
        total = int(re.search(r"issue text: (\d+)", text).group(1))
        likely = int(re.search(r"Likely rewritten by YouTrack: (\d+)", text).group(1))
        left = int(re.search(r"Likely left as written \(.*?\): (\d+)", text).group(1))
        urls = int(re.search(r"URLs \(YouTrack may or may not rewrite\): (\d+)", text).group(1))
        self.assertEqual(likely + left + urls, total)
        self.assertIn("URLs (YouTrack may or may not rewrite): 2 (1 in prose, references "
                      "if rewritten; 1 in code, Part B review if rewritten)", text)


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


class UnverifiableCrossIssue(unittest.TestCase):
    """Cross-issue checks that could not be made fail toward review (3), never clean (0)."""

    def setUp(self):
        # Reduced to a moved issue that is itself clean, so only the cross-issue
        # state can decide the verdict.
        self.before = fixture("ksa81-before.json")
        self.after = fixture("glass2-after.json")
        for snap in (self.before, self.after):
            snap["comments"] = [c for c in snap["comments"] if c["id"] == "7-101"]
        ref_b = self.before["referencing_issues"][0]
        ref_b["comments"][0]["text"] = "APP-43 remains blocked on KSA-81."
        self.after["referencing_issues"][0]["comments"][0]["text"] = \
            "APP-43 remains blocked on GLASS-2."

    def verdict(self, after):
        return yt_move.verdicts(yt_move.compare(self.before, after))

    def test_baseline_is_clean(self):
        self.assertEqual(self.verdict(self.after), ("PASS", "CLEAN", 0))

    def test_referencing_issue_missing_after_move(self):
        after = copy.deepcopy(self.after); after["referencing_issues"] = []
        self.assertEqual(self.verdict(after), ("PASS", "NEEDS REMEDIATION", 3))

    def test_referencing_issue_unreadable_after_move(self):
        after = copy.deepcopy(self.after)
        after["referencing_issues"] = [{"id": "3-77", "idReadable": "APP-43",
                                        "unreadable": "GET ... -> HTTP 404"}]
        rep = yt_move.compare(self.before, after)
        self.assertEqual(yt_move.verdicts(rep)[2], 3)
        self.assertIn("HTTP 404", rep["unverifiable_other_issues"][0]["reason"])

    def test_captured_comment_unreadable_after_move(self):
        after = copy.deepcopy(self.after)
        after["referencing_issues"][0]["comments"] = []
        rep = yt_move.compare(self.before, after)
        self.assertEqual(yt_move.verdicts(rep), ("PASS", "NEEDS REMEDIATION", 3))
        self.assertEqual(rep["unverifiable_other_issues"][0]["where"], "comment 7-201")

    def test_never_exit_0_and_never_1_on_its_own(self):
        for mutate in (lambda a: a.update(referencing_issues=[]),
                       lambda a: a["referencing_issues"][0].update(comments=[]),
                       lambda a: a["referencing_issues"][0].update(unreadable="x")):
            after = copy.deepcopy(self.after); mutate(after)
            self.assertEqual(self.verdict(after)[2], 3)

    def test_with_moved_issue_discrepancy_it_is_1(self):
        after = copy.deepcopy(self.after); after["referencing_issues"] = []
        comment(after, "7-101")["text"] = "edited by hand"
        self.assertEqual(self.verdict(after)[2], 1)

    def test_part_b_names_unverifiable_locations(self):
        after = copy.deepcopy(self.after)
        after["referencing_issues"][0]["comments"] = []
        rep = yt_move.compare(self.before, after)
        text = yt_move.followup_text("KSA-81", "GLASS-2", rep)
        self.assertIn("# Part B", text)
        self.assertIn("Could not be re-checked after the move", text)
        self.assertIn("- APP-43 comment 7-201:", text)
        self.assertIn("UNVERIFIABLE: APP-43 comment 7-201", yt_move.render(rep))


class CreateFollowupMocked(unittest.TestCase):
    """create_followup() with every API call captured; nothing reaches YouTrack."""

    PROTOS = {"157-2": ("Status", "StateIssueCustomField"),
              "157-0": ("Priority", "SingleEnumIssueCustomField"),
              "157-1": ("Type", "SingleEnumIssueCustomField"),
              "157-3": ("Assignee", "SingleUserIssueCustomField"),
              "157-15": ("Date time entered", "SimpleIssueCustomField"),
              "157-17": ("Repo URL", "SimpleIssueCustomField"),
              "157-32": ("Affected host", "SingleEnumIssueCustomField")}
    DISPLAY_NAMES = {"Claude_Code": "Claude Code"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        repo = os.path.join(self.tmp.name, "private-tools")
        os.makedirs(repo)
        import subprocess
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(["git", "-C", repo, "remote", "add", "origin",
                        "ssh://git@git.kevininscoe.com:2223/kinscoe/private-tools.git"], check=True)
        self.saved = (yt_move.api, yt_move.resolve_project, yt_move.FOLLOWUP_REPO,
                      yt_move.EVIDENCE_DIR)
        yt_move.FOLLOWUP_REPO = repo
        yt_move.EVIDENCE_DIR = os.path.join(self.tmp.name, "ticket-moves")
        os.makedirs(yt_move.EVIDENCE_DIR)
        for old, new in (("KSA-81", "GLASS-2"), ("KSA-117", "GLASS-3"), ("KTA-19", "GLASS-2")):
            for _, path in yt_move.evidence_paths(old, new):
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("evidence\n")
        yt_move.resolve_project = lambda name: {"id": "0-50", "shortName": name}
        self.calls, self.created = [], {}
        yt_move.api = self.fake_api

    def tearDown(self):
        (yt_move.api, yt_move.resolve_project, yt_move.FOLLOWUP_REPO,
         yt_move.EVIDENCE_DIR) = self.saved
        self.tmp.cleanup()

    def fake_api(self, method, path, params=None, body=None):
        self.calls.append((method, path, params, body))
        if method == "GET" and path == "/api/issues":
            return [{"customFields": [{"name": n, "$type": t, "projectCustomField":
                                       {"field": {"id": p}}} for p, (n, t) in self.PROTOS.items()]}]
        if method == "POST" and path == "/api/issues":
            self.created = body
            return {"id": "3-9999", "idReadable": "POE-99"}
        if method == "POST" and path.endswith("/comments"):
            self.comment = body["text"]
            return {"id": "7-1"}
        if method == "GET" and path == "/api/issues/3-9999":
            by_name = {f["name"]: f["value"] for f in self.created["customFields"]}
            fields = []
            for p, (n, _) in self.PROTOS.items():
                v = copy.deepcopy(by_name.get(n))
                if isinstance(v, dict) and "login" in v:
                    # What YouTrack really returns for a user: login plus display
                    # name. Omitting the name is how POE-27's bug got past this test.
                    v["name"] = self.DISPLAY_NAMES.get(v["login"], v["login"])
                fields.append({"projectCustomField": {"field": {"id": p}}, "value": v})
            return {"idReadable": "POE-99", "customFields": fields,
                    "description": self.created["description"],
                    "comments": [{"text": self.comment}]}
        raise AssertionError(f"unexpected call {method} {path}")

    def test_payload_and_read_back(self):
        rep = yt_move.compare(fixture("ksa81-before.json"), fixture("glass2-after.json"))
        out = yt_move.create_followup("KSA-81", "GLASS-2", rep, "~/tmp/r.json")
        body = self.created
        self.assertEqual(body["project"], {"id": "0-50"})
        self.assertTrue(body["summary"].startswith(
            "Update Markdown references and restore historical text after KSA-81"))
        f = {x["name"]: x for x in body["customFields"]}
        self.assertEqual(f["Status"]["value"], {"name": "Not yet started"})
        self.assertEqual(f["Priority"]["value"], {"name": "Normal"})
        self.assertEqual(f["Type"]["value"], {"name": "Task"})
        self.assertEqual(f["Assignee"]["value"], {"login": "Claude_Code"})
        self.assertIsInstance(f["Date time entered"]["value"], int)
        self.assertGreater(f["Date time entered"]["value"], 1_700_000_000_000)  # epoch ms
        self.assertEqual(f["Repo URL"]["value"], "https://git.kevininscoe.com/kinscoe/private-tools")
        self.assertEqual(f["Repo URL"]["$type"], "SimpleIssueCustomField")
        self.assertNotIn("Affected host", f)                 # not about one host
        self.assertNotIn("157-17", json.dumps(body))         # names, never prototype ids
        for part in ("Old issue ID: KSA-81\nNew issue ID: GLASS-2", "# Part A", "# Part B",
                     "searched all issues visible to the Claude_Code identity to exhaustion"):
            self.assertIn(part, body["description"])
        self.assertNotIn("N/A", body["description"])
        self.assertEqual(self.comment, "Repository: " + yt_move.FOLLOWUP_REPO)
        self.assertEqual(out["idReadable"], "POE-99")
        self.assertEqual(out["url"], "https://youtrack.kevininscoe.com/issue/POE-99")
        self.assertEqual(self.calls[-1][1], "/api/issues/3-9999")   # read back last

    def test_user_display_name_does_not_fail_read_back(self):
        # Regression for POE-27 (KSA-117 -> GLASS-3, 2026-10-04): the Assignee read
        # back as {"login": "Claude_Code", "name": "Claude Code"} and the helper
        # compared the name, so a correct ticket was reported wrong.
        out = yt_move.create_followup("KSA-117", "GLASS-3")
        self.assertEqual(out["idReadable"], "POE-99")
        self.assertIn("157-3", out["verified"])

    def test_wrong_assignee_login_still_fails(self):
        real = self.fake_api

        def other_user(method, path, params=None, body=None):
            r = real(method, path, params, body)
            if method == "GET" and path == "/api/issues/3-9999":
                for f in r["customFields"]:
                    if f["projectCustomField"]["field"]["id"] == "157-3":
                        f["value"] = {"login": "admin", "name": "Claude_Code"}
            return r
        yt_move.api = other_user
        with self.assertRaises(yt_move.Fail):
            yt_move.create_followup("KTA-19", "GLASS-2")

    def test_description_lists_every_evidence_file_by_full_path(self):
        out = yt_move.create_followup("KTA-19", "GLASS-2")
        paths = [p for _, p in yt_move.evidence_paths("KTA-19", "GLASS-2")]
        self.assertEqual(len(paths), 6)
        for p in paths:
            self.assertIn(f"- {p} — ", self.created["description"])
        self.assertEqual(out["evidence_paths"], paths)

    def test_missing_evidence_refuses_before_any_api_call(self):
        os.remove(yt_move.evidence_paths("KTA-19", "GLASS-2")[1][1])
        with self.assertRaises(yt_move.Fail) as cm:
            yt_move.create_followup("KTA-19", "GLASS-2")
        self.assertIn("GLASS-2-after-project-move.md", str(cm.exception))
        self.assertEqual(self.calls, [])

    def test_empty_evidence_refuses(self):
        open(yt_move.evidence_paths("KTA-19", "GLASS-2")[0][1], "w").close()
        with self.assertRaises(yt_move.Fail):
            yt_move.create_followup("KTA-19", "GLASS-2")
        self.assertEqual(self.calls, [])

    def test_evidence_path_lost_on_read_back_raises(self):
        real = self.fake_api

        def truncating(method, path, params=None, body=None):
            r = real(method, path, params, body)
            if method == "GET" and path == "/api/issues/3-9999":
                r["description"] = r["description"].replace("preservation-check.json", "")
            return r
        yt_move.api = truncating
        with self.assertRaises(yt_move.Fail) as cm:
            yt_move.create_followup("KTA-19", "GLASS-2")
        self.assertIn("Evidence paths", str(cm.exception))

    def test_part_a_only_without_remediation(self):
        yt_move.create_followup("KTA-19", "GLASS-2")
        self.assertNotIn("# Part B", self.created["description"])
        self.assertEqual(self.created["summary"],
                         "Update Markdown references after KTA-19 moved to GLASS-2")

    def test_wrong_read_back_raises(self):
        real = self.fake_api

        def lying(method, path, params=None, body=None):
            r = real(method, path, params, body)
            if method == "GET" and path == "/api/issues/3-9999":
                r["customFields"][0]["value"] = {"name": "To do"}
            return r
        yt_move.api = lying
        with self.assertRaises(yt_move.Fail):
            yt_move.create_followup("KTA-19", "GLASS-2")

    def test_no_repo_url_is_invented(self):
        yt_move.FOLLOWUP_REPO = os.path.join(self.tmp.name, "missing")
        with self.assertRaises(yt_move.Fail):
            yt_move.create_followup("KTA-19", "GLASS-2")
        self.assertEqual(self.calls, [])      # refused before any API call

    def test_forge_url(self):
        self.assertEqual(yt_move.forge_url("ssh://git@git.kevininscoe.com:2223/kinscoe/x.git"),
                         "https://git.kevininscoe.com/kinscoe/x")
        self.assertEqual(yt_move.forge_url("git@github.com:kevinpinscoe/skills.git"),
                         "https://github.com/kevinpinscoe/skills")
        self.assertIsNone(yt_move.forge_url("/some/local/path"))


class MoveMocked(unittest.TestCase):
    """move(): the exact call it makes, and that an ignored move still fails."""

    def setUp(self):
        self.saved = (yt_move.api, yt_move.resolve_project)
        self.calls, self.project = [], {"id": "0-35", "shortName": "KSA"}
        yt_move.resolve_project = lambda pid: {"id": pid, "shortName": "GLASS",
                                               "name": "bao-breakglass", "searchable_issue": True}
        yt_move.api = self.fake_api
        self.honour = True

    def tearDown(self):
        yt_move.api, yt_move.resolve_project = self.saved

    def fake_api(self, method, path, params=None, body=None):
        self.calls.append((method, path, body))
        if method == "GET":
            return {"id": "3-2405", "idReadable": "KSA-117" if self.project["id"] == "0-35"
                    else "GLASS-3", "summary": "s", "project": dict(self.project)}
        if method == "POST" and self.honour:
            self.project = {"id": body["project"]["id"], "shortName": "GLASS"}
        return {}

    def test_uses_issue_update_form(self):
        out = yt_move.move("3-2405", "0-66")
        posts = [c for c in self.calls if c[0] == "POST"]
        self.assertEqual(posts, [("POST", "/api/issues/3-2405", {"project": {"id": "0-66"}})])
        self.assertNotIn("/api/issues/3-2405/project", [c[1] for c in self.calls])
        self.assertEqual(out["idReadable"], "GLASS-3")
        self.assertEqual(self.calls[-1][0], "GET")        # re-read after the write

    def test_ignored_move_fails(self):
        self.honour = False                               # the KSA-117 behaviour
        with self.assertRaises(yt_move.Fail) as ctx:
            yt_move.move("3-2405", "0-66")
        self.assertIn("issue is in KSA", str(ctx.exception))


class UtilityBootstrapProtocol(unittest.TestCase):
    """Part A decides who creates the shared utility from repository state.

    Regression for POE-27/POE-28 (2026-10-05): every follow-up said "create the
    utility", so POE-28 waited on POE-27's plan while no implementation existed.
    """

    def setUp(self):
        self.text = yt_move.followup_text("KTA-19", "GLASS-2")
        self.a3 = self.text[self.text.index("## A3"):self.text.index("## A4")]

    def test_no_ticket_is_named_as_creator(self):
        self.assertIsNone(re.search(r"\bPOE-\d+", self.text))
        for phrase in ("first ticket", "created first", "older ticket", "creation order"):
            self.assertNotIn(phrase, self.text.lower())

    def test_never_waits_on_an_open_ticket(self):
        low = self.text.lower()
        for phrase in ("if another open ticket exists, wait", "another ticket creates",
                       "that poe", "creates the utility"):
            self.assertNotIn(phrase, low)
        self.assertIn("An open POE ticket is not a lock. A planned implementation is not a lock.",
                      self.text)

    def test_case_1_reuse_from_main_after_validation(self):
        self.assertIn("### Case 1 — the utility already exists on `private-tools` main", self.a3)
        for need in ("tracked by git on `main`", "Run its tests", "reuse it",
                     "Do not create another implementation",
                     "does not meet the A4 contract, STOP"):
            self.assertIn(need, self.a3)
        self.assertIn("ls-tree --name-only origin/main -- yt-rewrite-moved-issue-id.py", self.a3)

    def test_case_2_concrete_state_not_tickets(self):
        self.assertIn("### Case 2 — absent from main, but a concrete implementation is in progress",
                      self.a3)
        self.assertIn("Another open POE issue is not, by itself, proof", self.a3)
        for need in ("open `private-tools` pull request", "pushed branch",
                     "committed implementation", "STOP before performing any rewrite",
                     "Never write a competing copy", "two genuinely active concrete implementations"):
            self.assertIn(need, self.a3)

    def test_case_3_current_ticket_bootstraps_via_prerequisite_pr(self):
        self.assertIn("### Case 3 — absent, and no concrete implementation exists", self.a3)
        self.assertIn("**This POE ticket becomes the bootstrap owner.**", self.a3)
        case3 = self.a3[self.a3.index("### Case 3"):]
        order = ["Implement the canonical utility", "Add the tests", "Run the tests",
                 "Open a `private-tools` pull request",
                 "STOP before using the utility for any cross-repository rewrite",
                 "Ask Kevin to merge that prerequisite", "fast-forward `~/private-tools` main",
                 "rerun its tests from main", "continue with A6"]
        positions = [case3.index(step) for step in order]
        self.assertEqual(positions, sorted(positions))

    def test_rewrites_only_after_a3(self):
        a6 = self.text[self.text.index("## A6"):]
        self.assertIn("Only once A3 has established a tested utility on `private-tools` main", a6)

    def test_full_utility_contract(self):
        a4 = self.text[self.text.index("## A4"):self.text.index("## A5")]
        for need in ("yt-rewrite-moved-issue-id.py OLD_ID NEW_ID FILE",
                     "exactly one explicitly named file", "Never recursively search",
                     "only a regular `.md` file", "Refuse symlinks and non-regular files",
                     "^[A-Z][A-Z0-9_]*-[1-9][0-9]*$", "OLD_ID equals NEW_ID", "Escape OLD_ID",
                     "(?<![A-Za-z0-9-])OLD_ID(?![0-9])", "Never use unrestricted `str.replace()`",
                     "zero boundary-aware matches", "exact number of substitutions",
                     "no line-ending normalisation", "permission mode",
                     "temporary file in the same directory", "remove the temporary file",
                     "Exit non-zero", "against the exact expected regex-substitution result",
                     "never print unrelated file contents"):
            self.assertIn(need, a4)
        self.assertEqual(len(re.findall(r"^\d+\. ", a4, re.M)), 18)

    def test_required_utility_tests(self):
        a5 = self.text[self.text.index("## A5"):self.text.index("## A6")]
        for need in ("`KTA-19`", "`(KTA-19)`", "`KTA-19.`", "`KTA-19,`",
                     "`https://youtrack.kevininscoe.com/issue/KTA-19`", "`KTA-190`", "`KTA-191`",
                     "`XKTA-19`", "`ABC-KTA-19`", "Several approved matches",
                     "Zero matches: refused, file unchanged", "invalid old ID", "invalid new ID",
                     "identical old and new IDs", "non-`.md` file, a directory, and a symlink",
                     "Permission mode preserved", "CRLF input stays CRLF", "no final newline",
                     "failed atomic write leaves the original intact",
                     "second invocation after a successful rewrite refuses",
                     "Temporary fixtures only"):
            self.assertIn(need, a5)

    def test_rg_ban_and_artifact_review_kept(self):
        self.assertIn("AI agents are forbidden from running recursive `rg`", self.text)
        self.assertIn("**Do not rerun `rg`**", self.text)
        self.assertIn("**Required:** before changing a Markdown hit that looks like a branch name",
                      self.text)
        self.assertIn("Never use recursive `rg` to verify", self.text)

    # ---- PR 24 review: worktree path mapping (A6)
    def test_a6_inventory_is_authority_worktree_is_target(self):
        a6 = self.text[self.text.index("## A6"):]
        self.assertIn("The inventory path is the authority for *which* file may change; "
                      "the corresponding worktree path is *where* it is changed.", a6)
        self.assertIn("Use only paths explicitly present in the inventory", a6)
        self.assertIn("Only then run `yt-rewrite-moved-issue-id.py` against the **worktree copy**", a6)

    def test_a6_forbids_editing_the_main_checkout_path(self):
        a6 = self.text[self.text.index("## A6"):]
        self.assertIn("**Never modify the original inventory pathname in the main checkout**", a6)

    def test_a6_requires_relative_path_mapping_in_order(self):
        a6 = self.text[self.text.index("## A6"):]
        steps = ["Determine whether it belongs to a Git repository",
                 "the repository's normal (main) working tree",
                 "Derive the path relative to the repository root",
                 "tracked by Git on the base the POE worktree is made from",
                 "Create or use this POE ticket's worktree",
                 "Build the candidate target inside the POE worktree from that same relative path",
                 "Check containment both ways",
                 "against the **worktree copy**", "Review the worktree diff",
                 "open that repository's pull request"]
        pos = [a6.index(x) for x in steps]
        self.assertEqual(pos, sorted(pos))
        self.assertIn("preserving nested directories exactly", a6)
        self.assertIn("`~/Projects/private/host-frodo-config/ai-wt/<this issue>/README.md`", a6)

    def test_a6_no_target_outside_the_worktree(self):
        a6 = self.text[self.text.index("## A6"):]
        self.assertIn("No file outside the worktree may be substituted as a target.", a6)

    # ---- PR 24 second review: real-path containment (A6)
    def a6(self):
        return self.text[self.text.index("## A6"):]

    def test_a6_both_lexical_and_resolved_containment(self):
        self.assertIn("**Both lexical and resolved containment are required. A symlinked "
                      "directory must not allow the rewrite target to escape the POE worktree.**",
                      self.a6())

    def test_a6_resolved_containment_is_path_aware(self):
        a6 = self.a6()
        for need in ("resolve the worktree root canonically", "Path.resolve(strict=True)",
                     "`Path.is_relative_to`", "`os.path.commonpath`",
                     "never by string-prefix comparison",
                     "Reject a target that escapes through any symlinked component",
                     "must be a regular file and not a symlink (`os.lstat`)",
                     "contain no `..` component"):
            self.assertIn(need, a6)
        self.assertNotIn("resolves lexically beneath that worktree root", a6)   # ecdf169

    def test_a6_containment_checked_before_the_utility_runs(self):
        a6 = self.a6()
        self.assertLess(a6.index("Check containment both ways"),
                        a6.index("Only then run `yt-rewrite-moved-issue-id.py`"))

    # ---- PR 24 second review: unmanaged / untracked / other-worktree paths (A6)
    def test_a6_untracked_and_non_git_paths_fail_closed(self):
        a6 = self.a6()
        self.assertIn("**Unmanaged or unmappable approved paths fail closed.**", a6)
        for need in ("is outside any Git repository", "is untracked",
                     "belongs to another worktree rather than the normal checkout",
                     "no corresponding tracked file in the new POE worktree",
                     "STOP for that file"):
            self.assertIn(need, a6)

    def test_a6_other_worktree_is_not_a_source_checkout(self):
        self.assertIn("not an `ai-wt/` or other linked worktree", self.a6())
        self.assertIn("--git-common-dir", self.a6())

    def test_a6_tracked_on_the_worktree_base(self):
        self.assertIn("ls-tree --name-only <base> -- <relative path>", self.a6())

    def test_a6_unmappable_reported_never_dropped_or_edited_in_place(self):
        a6 = self.a6()
        self.assertIn("Report it to Kevin as an unmanaged/unmappable approved path", a6)
        self.assertIn("Never fall back to editing the original inventory pathname", a6)
        self.assertIn("never silently drop it from the approved set", a6)

    # ---- PR 24 review: stale branches are not locks (A3)
    def test_a3_branch_with_file_is_not_automatically_owner(self):
        self.assertIn("**File presence is not ownership.**", self.a3)
        self.assertIn("A hit is evidence to investigate, not a lock: file existence on a remote "
                      "branch is not sufficient.", self.a3)
        self.assertNotIn("a pushed branch containing it, or", self.a3)   # 1433e7d wording

    def test_a3_branch_needs_current_ownership_evidence(self):
        self.assertIn("a pushed branch with committed implementation **plus** current recorded "
                      "ownership tying it to an active ticket or lane", self.a3)
        self.assertIn("Confirm that the branch is actively owned by a current implementation "
                      "ticket/lane or open PR. Otherwise report the stale/unowned branch and "
                      "continue determining whether the current ticket should bootstrap the "
                      "utility.", self.a3)

    def test_a3_stale_branches_are_not_locks(self):
        for need in ("a remote branch containing the file with no current owning ticket, lane "
                     "or pull request", "an old merged branch", "an abandoned or stale branch",
                     "neither does a stale or unowned branch that contains the file",
                     "ask Kevin rather than assuming it owns the implementation"):
            self.assertIn(need, self.a3)

    def test_a3_two_active_implementations_still_go_to_kevin(self):
        self.assertIn("If two genuinely active concrete implementations exist at the same time, "
                      "STOP both paths and ask Kevin", self.a3)

    # ---- PR 24 review: safe-write sequence (A4, A5)
    def test_a4_safe_write_sequence_in_order(self):
        a4 = self.text[self.text.index("## A4"):self.text.index("## A5")]
        seq = ["Read the original bytes", "Compute the expected output entirely in memory",
               "Create a temporary file in the same directory",
               "Write the complete expected bytes", "Flush and `fsync` the temporary file",
               "Re-read the temporary file and verify",
               "Give the temporary file the original's permission mode",
               "Only then atomically replace the original",
               "Re-read the final pathname and verify",
               "remove the temporary file if it still exists"]
        pos = [a4.index(x) for x in seq]
        self.assertEqual(pos, sorted(pos))
        self.assertIn("A failure at any step before the replacement leaves the original untouched",
                      a4)

    def test_a4_does_not_promise_restore_after_rename(self):
        a4 = self.text[self.text.index("## A4"):self.text.index("## A5")]
        self.assertIn("keeps no backup", a4)
        self.assertIn("does not restore the old content", a4)

    def test_a5_pre_replace_verification_failure_test(self):
        a5 = self.text[self.text.index("## A5"):self.text.index("## A6")]
        self.assertIn("A simulated pre-replacement verification failure (step 6 reads back "
                      "different bytes) leaves the original byte-for-byte unchanged", a5)

    def test_same_protocol_with_part_b(self):
        rep = yt_move.compare(fixture("ksa81-before.json"), fixture("glass2-after.json"))
        text = yt_move.followup_text("KSA-81", "GLASS-2", rep)
        self.assertIn("**This POE ticket becomes the bootstrap owner.**", text)
        self.assertIn("# Part B", text)


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
            "see (https://youtrack.kevininscoe.com/issue/KSA-81).": "reference",
            "`https://youtrack.kevininscoe.com/issue/KSA-81`": "artifact",
            "```\ncurl https://youtrack.kevininscoe.com/issue/KSA-81\n```": "artifact",
            "~~~\ncurl https://youtrack.kevininscoe.com/issue/KSA-81\n~~~": "artifact",
            "``open https://youtrack.kevininscoe.com/issue/KSA-81``": "artifact",
            "~~~\nx\n~~~\nsee https://youtrack.kevininscoe.com/issue/KSA-81": "reference",
            "``a`` see https://youtrack.kevininscoe.com/issue/KSA-81": "reference",
            "a ` stray, then https://youtrack.kevininscoe.com/issue/KSA-81": "reference",
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


class CodeContextTests(unittest.TestCase):
    """Markdown code detection behind classify()'s "code wins" rule."""

    def ctx(self, text, marker="X"):
        return yt_move.code_context(text, text.index(marker))

    def test_fences(self):
        self.assertEqual(self.ctx("```\nX\n```"), "code block")
        self.assertEqual(self.ctx("~~~\nX\n~~~"), "code block")
        self.assertEqual(self.ctx("  ~~~~ text\nX"), "code block")       # unclosed, info string
        self.assertEqual(self.ctx("```bash X\n```"), "code block")       # the opening line
        self.assertIsNone(self.ctx("```\na\n```\nX"))
        self.assertIsNone(self.ctx("~~~\na\n~~~\nX"))

    def test_fence_closes_only_on_matching_delimiter(self):
        self.assertEqual(self.ctx("~~~\n```\nX\n~~~"), "code block")   # ``` cannot close ~~~
        self.assertEqual(self.ctx("````\n```\nX\n````"), "code block")  # shorter cannot close
        self.assertEqual(self.ctx("```\na\n``` trailing\nX"), "code block")  # text after: not a close
        self.assertIsNone(self.ctx("```\na\n`````\nX"))                 # longer closes

    def test_inline_spans(self):
        self.assertEqual(self.ctx("a `X` b"), "inline code")
        self.assertEqual(self.ctx("a ``X`` b"), "inline code")
        self.assertEqual(self.ctx("a `` `X` `` b"), "inline code")       # single ticks inside double
        self.assertIsNone(self.ctx("a `b` X"))
        self.assertIsNone(self.ctx("a ``b`` X"))
        self.assertIsNone(self.ctx("a ` X"))                             # unmatched run is literal
        self.assertIsNone(self.ctx("a ``b` X"))                          # run lengths differ


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
        self.assertIn("--glob '*.md'", text)
        self.assertIn("~/private-tools/yt-rewrite-moved-issue-id.py", text)
        self.assertIn("# Part A", text)
        self.assertNotIn("# Part B", text)
        self.assertEqual(yt_move.followup_summary("KTA-19", "GLASS-2"),
                         "Update Markdown references after KTA-19 moved to GLASS-2")

    def test_inventory_excludes_and_is_archived(self):
        text = yt_move.followup_text("KTA-19", "GLASS-2")
        inv = "~/archives/youtrack/ticket-moves/KTA-19-home-markdown-references.txt"
        self.assertEqual(yt_move.inventory_path("KTA-19"), inv)
        for opt in ("--no-config", "--hidden", "--no-ignore", "--no-follow",
                    "--with-filename", "--line-number", "--no-heading", "--color=never",
                    "--glob '!.git/'", "--glob '!/tmp/'", "--glob '!/Downloads/'",
                    "--glob '!/archives/youtrack/ticket-moves/'"):
            self.assertIn(opt, text)
        self.assertNotIn("~/tmp/KTA-19-home-markdown-references", text)
        self.assertNotIn("That is accepted", text)
        self.assertIn("kept for audit", text)
        self.assertIn("`.MD` and `.markdown` files are outside this scope", text)
        self.assertIn("never proves that no reference to KTA-19 exists", text)
        # Both helpers are given in full, with one bash line each.
        self.assertIn(yt_move.inventory_script("KTA-19").rstrip(), text)
        self.assertIn(yt_move.inventory_selftest_script("KTA-19").rstrip(), text)
        self.assertIn("`bash ~/tmp/KTA-19-markdown-inventory-selftest.sh`", text)
        self.assertIn("`bash ~/tmp/KTA-19-markdown-inventory.sh`", text)
        # The inventory is produced later, by the POE work; it must not gate creation.
        self.assertNotIn(inv, [p for _, p in yt_move.evidence_paths("KTA-19", "GLASS-2")])

    def test_with_remediation(self):
        rep = yt_move.compare(fixture("ksa81-before.json"), fixture("glass2-after.json"))
        text = yt_move.followup_text("KSA-81", "GLASS-2", rep, "~/tmp/r.json")
        self.assertIn("# Part A", text)
        self.assertIn("# Part B", text)
        self.assertIn("Never mass-replace GLASS-2 back to KSA-81", text)
        self.assertIn("~/archives/youtrack/ticket-moves/KSA-81-before-project-move.api.json", text)
        self.assertNotIn("~/tmp/KSA-81-before-project-move", text)
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


STUB_RG = r"""#!/usr/bin/env bash
# Stand-in for rg: records how it was called and behaves per $STUB_MODE.
# No real search ever runs in these tests.
printf '%s\n' "$PWD" > "$STUB_LOG.cwd"
printf '%s\n' "$@" > "$STUB_LOG.args"
printf '%s' "$STUB_PROMPT" >&2
root=${@: -1}
case $STUB_MODE in
  hits) printf '%s\n' "$root/notes/a.md:3:see KTA-19 here"; exit 0 ;;
  empty) exit 1 ;;
  refused) echo "rg: not confirmed -- denying." >&2; exit 1 ;;
  error) printf '%s\n' "$root/notes/a.md:3:partial"; echo "rg: some error" >&2; exit 2 ;;
  race) printf 'OTHER\n' > "$STUB_INVENTORY"; printf '%s\n' "$root/a.md:1:KTA-19"; exit 0 ;;
  interrupt) printf '%s\n' "$root/a.md:1:partial"; kill -TERM "$PPID"; sleep 0.2; exit 0 ;;
  selftest-pass|selftest-extra)
    for p in notes/normal.md .hidden/hidden.md ignored/ignored.md repo/gi/gitignored.md repo/tmp/nested.md; do
      printf '%s\n' "$root/$p:2:see KTA-19 here"
    done
    [[ $STUB_MODE == selftest-extra ]] && printf '%s\n' "$root/tmp/scratch.md:2:see KTA-19 here"
    exit 0 ;;
esac
exit 99
"""


class InventoryHelperTests(unittest.TestCase):
    """The generated helpers, run end to end against a stub rg on PATH."""

    OLD = "KTA-19"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.home = os.path.join(t, "home")
        self.elsewhere = os.path.join(t, "elsewhere")
        self.bin = os.path.join(t, "bin")
        self.fixtures = os.path.join(t, "fixtures-tmp")
        for d in (self.home, self.elsewhere, self.bin, self.fixtures):
            os.makedirs(d)
        with open(os.path.join(self.bin, "rg"), "w") as fh:
            fh.write(STUB_RG)
        os.chmod(os.path.join(self.bin, "rg"), 0o755)
        self.log = os.path.join(t, "stub")
        self.evidence = os.path.join(self.home, "archives/youtrack/ticket-moves")
        self.inventory = os.path.join(self.evidence, f"{self.OLD}-home-markdown-references.txt")

    def tearDown(self):
        self.tmp.cleanup()

    def run_helper(self, script, mode, prompt=yt_move.WRAPPER_PROMPT):
        path = os.path.join(self.tmp.name, "helper.sh")
        with open(path, "w") as fh:
            fh.write(script)
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": self.home, "TMPDIR": self.fixtures,
               "STUB_MODE": mode, "STUB_LOG": self.log, "STUB_PROMPT": prompt,
               "STUB_INVENTORY": self.inventory, "RIPGREP_CONFIG_PATH": "/nonexistent"}
        return subprocess.run(["bash", path], cwd=self.elsewhere, env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=30)

    def stub_args(self):
        with open(self.log + ".args") as fh:
            return fh.read().splitlines()

    def stub_cwd(self):
        with open(self.log + ".cwd") as fh:
            return fh.read().strip()

    def leftovers(self):
        return [n for n in os.listdir(self.evidence) if n.startswith(".")]

    def read_inventory(self):
        with open(self.inventory) as fh:
            return fh.read()

    # -- the inventory helper ----------------------------------------------------

    def test_syntax(self):
        for script in (yt_move.inventory_script(self.OLD), yt_move.inventory_selftest_script(self.OLD)):
            r = subprocess.run(["bash", "-n"], input=script, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_hits_published_and_search_runs_from_home(self):
        r = self.run_helper(yt_move.inventory_script(self.OLD), "hits")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read_inventory(), f"{self.home}/notes/a.md:3:see KTA-19 here\n")
        self.assertIn("(1 matching lines)", r.stdout)
        self.assertEqual(self.stub_cwd(), self.home)  # launched from elsewhere
        self.assertEqual(self.leftovers(), [])

    def test_exact_rg_arguments(self):
        self.run_helper(yt_move.inventory_script(self.OLD), "hits")
        args = self.stub_args()
        expected = list(yt_move.INVENTORY_RG_OPTIONS)
        for g in yt_move.INVENTORY_GLOBS:
            expected += ["--glob", g]
        expected += ["--", yt_move.boundary_pattern(self.OLD), self.home]
        self.assertEqual(args, expected)
        for flag in ("--hidden", "--no-ignore", "--no-config", "--no-follow", "--with-filename",
                     "--line-number", "--no-heading", "--color=never"):
            self.assertIn(flag, args)
        for g in ("*.md", "!.git/", "!/tmp/", "!/Downloads/", "!/archives/youtrack/ticket-moves/"):
            self.assertIn(g, args)
        self.assertNotIn("-L", args)
        self.assertNotIn("--follow", args)

    def test_zero_hits_is_a_kept_empty_inventory(self):
        r = self.run_helper(yt_move.inventory_script(self.OLD), "empty")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read_inventory(), "")
        self.assertIn("Zero hits within the covered scope", r.stdout)
        self.assertEqual(self.leftovers(), [])

    def test_wrapper_refusal_is_not_an_empty_inventory(self):
        r = self.run_helper(yt_move.inventory_script(self.OLD), "refused")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(os.path.exists(self.inventory))
        self.assertIn("Not treating that as an empty result", r.stderr)
        self.assertEqual(self.leftovers(), [])

    def test_exit_1_without_the_prompt_still_counts_as_empty(self):
        r = self.run_helper(yt_move.inventory_script(self.OLD), "empty", prompt="")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read_inventory(), "")

    def test_failed_search_keeps_nothing(self):
        r = self.run_helper(yt_move.inventory_script(self.OLD), "error")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(os.path.exists(self.inventory))
        self.assertIn("rg exited 2", r.stderr)
        self.assertEqual(self.leftovers(), [])

    def test_interrupted_search_keeps_nothing(self):
        r = self.run_helper(yt_move.inventory_script(self.OLD), "interrupt")
        self.assertEqual(r.returncode, 143)
        self.assertFalse(os.path.exists(self.inventory))
        self.assertEqual(self.leftovers(), [])

    def test_existing_inventory_is_refused_untouched(self):
        os.makedirs(self.evidence)
        with open(self.inventory, "w") as fh:
            fh.write("KEEP\n")
        r = self.run_helper(yt_move.inventory_script(self.OLD), "hits")
        self.assertEqual(r.returncode, 1)
        self.assertIn("already exists", r.stderr)
        self.assertEqual(self.read_inventory(), "KEEP\n")
        self.assertFalse(os.path.exists(self.log + ".args"))  # rg never ran
        self.assertEqual(self.leftovers(), [])

    def test_inventory_appearing_during_the_run_is_not_overwritten(self):
        r = self.run_helper(yt_move.inventory_script(self.OLD), "race")
        self.assertEqual(r.returncode, 1)
        self.assertIn("appeared during the run", r.stderr)
        self.assertEqual(self.read_inventory(), "OTHER\n")
        self.assertEqual(self.leftovers(), [])

    # -- the self-test helper ----------------------------------------------------

    def test_helpers_share_one_search_definition(self):
        block = yt_move.inventory_search_block(self.OLD)
        self.assertIn(block, yt_move.inventory_script(self.OLD))
        self.assertIn(block, yt_move.inventory_selftest_script(self.OLD))

    def test_selftest_pass_cleans_up(self):
        r = self.run_helper(yt_move.inventory_selftest_script(self.OLD), "selftest-pass")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS:", r.stdout)
        cwd = self.stub_cwd()
        self.assertTrue(cwd.startswith(self.fixtures) and cwd.endswith("/home"), cwd)
        self.assertEqual(self.stub_args()[-1], cwd)
        self.assertEqual(os.listdir(self.fixtures), [])
        self.assertFalse(os.path.exists(self.evidence))  # never touches the real inventory

    def test_selftest_unexpected_hit_fails_and_cleans_up(self):
        r = self.run_helper(yt_move.inventory_selftest_script(self.OLD), "selftest-extra")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL:", r.stdout)
        self.assertIn("tmp/scratch.md:2:see KTA-19 here", r.stdout)
        self.assertEqual(os.listdir(self.fixtures), [])

    def test_selftest_missing_hits_fail_and_clean_up(self):
        r = self.run_helper(yt_move.inventory_selftest_script(self.OLD), "empty")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL:", r.stdout)
        self.assertEqual(os.listdir(self.fixtures), [])

    def test_selftest_interrupt_cleans_up(self):
        r = self.run_helper(yt_move.inventory_selftest_script(self.OLD), "interrupt")
        self.assertEqual(r.returncode, 143)
        self.assertEqual(os.listdir(self.fixtures), [])

    def test_selftest_fixture_covers_the_contract(self):
        script = yt_move.inventory_selftest_script(self.OLD)
        for want in ("mk .hidden/hidden.md", "mk ignored/ignored.md", "printf 'ignored/\\n' > \"$root/.ignore\"",
                     "mk repo/tmp/nested.md", "mk tmp/scratch.md", "mk Downloads/download.md",
                     "mk archives/youtrack/ticket-moves/evidence.md", "mk .git/top.md",
                     "mk repo/.git/repo.md", "mk repo/sub/deep/.git/deep.md",
                     "mk notes/boundary.md KTA-190 XKTA-19 ABC-KTA-19",
                     'ln -s -- "$outside/dir" "$root/linkdir"', 'ln -s -- "$outside/file.md" "$root/link.md"'):
            self.assertIn(want, script)


if __name__ == "__main__":
    unittest.main(verbosity=1)
