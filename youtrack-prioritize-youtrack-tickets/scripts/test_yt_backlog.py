#!/usr/bin/env python3
"""Offline tests for yt_backlog.py. No API call, no credentials, no live write.

yt_backlog.api is replaced by FakeYouTrack, an in-memory model of the endpoints
the helper uses. It can cap page sizes, fail a write before or after it lands,
and accept a write while doing nothing, which is how the retry and read-back
rules are exercised.

Run: python3 test_yt_backlog.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import yt_backlog as yb  # noqa: E402

PROTOS = {"Status": ("157-2", "StateIssueCustomField"),
          "Priority": ("157-0", "SingleEnumIssueCustomField"),
          "Type": ("157-1", "SingleEnumIssueCustomField"),
          "Assignee": ("157-3", "SingleUserIssueCustomField"),
          "Affected host": ("157-32", "SingleEnumIssueCustomField"),
          "Date time entered": ("157-15", "SimpleIssueCustomField")}
BUNDLES = {"Status": ["To do", "In Progress", "Done", "BLOCKED", "Backlog", "Consider",
                      "Not yet started", "Wont do"],
           "Priority": ["Show-stopper", "Critical", "Major", "Normal", "Minor"],
           "Type": ["Bug", "Feature", "Task", "Epic"],
           "Affected host": ["FLDW", "web1", "core"]}
LINK_TYPES = [
    {"id": "L-0", "name": "Relates", "sourceToTarget": "relates to", "targetToSource": "",
     "directed": False, "aggregation": False},
    {"id": "L-1", "name": "Depend", "sourceToTarget": "is required for",
     "targetToSource": "depends on", "directed": True, "aggregation": False},
    {"id": "L-2", "name": "Duplicate", "sourceToTarget": "is duplicated by",
     "targetToSource": "duplicates", "directed": True, "aggregation": True},
    {"id": "L-3", "name": "Subtask", "sourceToTarget": "parent for",
     "targetToSource": "subtask of", "directed": True, "aggregation": True},
]


class FakeYouTrack:
    def __init__(self, page_cap=100):
        self.page_cap = page_cap
        self.projects = [{"id": "0-1", "shortName": "GLASS", "name": "Glass house"},
                         {"id": "0-2", "shortName": "OTHER", "name": "Other things"},
                         {"id": "0-3", "shortName": "GLASSY", "name": "Glass polish"},
                         {"id": "0-9", "shortName": "TMPL", "name": "Project template"}]
        self.issues = {}
        self.counter = 0
        self.faults = []      # {"method", "match", "mode"}: error-before | error-after | noop
        self.writes = []
        self.stall = False
        self.status_proto = "157-2"

    # -- building ------------------------------------------------------------
    def add(self, readable, summary="", status="Backlog", priority="Normal", type_="Task",
            host=None, resolved=None, parent=None, description="", comments=()):
        self.counter += 1
        eid = f"3-{self.counter}"
        self.issues[eid] = {
            "id": eid, "idReadable": readable, "project": readable.rsplit("-", 1)[0],
            "summary": summary or f"Summary of {readable}", "description": description,
            "resolved": resolved, "parent": None, "depends_on": [], "relates": [],
            "fields": {"Status": status, "Priority": priority, "Type": type_,
                       "Affected host": host, "Assignee": None, "Date time entered": 1},
            "comments": [{"id": f"7-{n}", "text": t, "created": n, "deleted": False,
                          "author": {"login": "admin"}} for n, t in enumerate(comments)],
        }
        if parent:
            self.issues[eid]["parent"] = self.eid(parent)
        return eid

    def eid(self, readable):
        for i in self.issues.values():
            if i["idReadable"] == readable:
                return i["id"]
        raise KeyError(readable)

    def get(self, readable):
        return self.issues[self.eid(readable)]

    def depend(self, dependent, prerequisite):
        self.get(dependent)["depends_on"].append(self.eid(prerequisite))

    def relate(self, a, b):
        self.get(a)["relates"].append(self.eid(b))

    def children(self, readable):
        eid = self.eid(readable)
        return sorted(i["idReadable"] for i in self.issues.values() if i["parent"] == eid)

    # -- rendering -----------------------------------------------------------
    def _custom_fields(self, issue):
        out = []
        for name, (proto, type_) in PROTOS.items():
            if name == "Status":
                proto = self.status_proto
            value = issue["fields"].get(name)
            if name == "Assignee":
                value = {"login": value} if value else None
            elif name != "Date time entered":
                value = {"name": value} if value else None
            pcf = {"field": {"id": proto}}
            if name in BUNDLES:
                pcf["bundle"] = {"values": [{"name": v, "archived": False}
                                            for v in BUNDLES[name]]}
            out.append({"id": f"F-{name}", "name": name, "$type": type_,
                        "projectCustomField": pcf, "value": value})
        return out

    def _render(self, issue):
        parent = self.issues.get(issue["parent"])
        return {"id": issue["id"], "idReadable": issue["idReadable"],
                "summary": issue["summary"], "description": issue["description"],
                "created": 1, "updated": 2, "resolved": issue["resolved"],
                "project": {"id": "0-1", "shortName": issue["project"]},
                "customFields": self._custom_fields(issue),
                "parent": {"issues": [{"id": parent["id"], "idReadable": parent["idReadable"],
                                       "summary": parent["summary"],
                                       "project": {"shortName": parent["project"]}}]
                           if parent else []}}

    def _linked(self, issue, link_id):
        eid = issue["id"]
        others = self.issues.values()
        if link_id == "L-0":
            ids = issue["relates"] + [o["id"] for o in others if eid in o["relates"]]
        elif link_id == "L-1s":   # this issue is required for ...
            ids = [o["id"] for o in others if eid in o["depends_on"]]
        elif link_id == "L-1t":   # this issue depends on ...
            ids = list(issue["depends_on"])
        elif link_id == "L-3s":   # parent for ...
            ids = [o["id"] for o in others if o["parent"] == eid]
        elif link_id == "L-3t":
            ids = [issue["parent"]] if issue["parent"] else []
        else:
            ids = []
        return [self.issues[i] for i in ids]

    def _links(self, issue):
        out = []
        for lt in LINK_TYPES:
            sides = [("OUTWARD", "s"), ("INWARD", "t")] if lt["directed"] else [("BOTH", "")]
            for direction, suffix in sides:
                lid = lt["id"] + suffix
                out.append({"id": lid, "direction": direction, "linkType": lt,
                            "issues": [{"id": o["id"]} for o in self._linked(issue, lid)]})
        return out

    def _page(self, items, params):
        if self.stall:
            return items[:1]
        skip = int(params.get("$skip", 0))
        top = min(int(params.get("$top", 42)), self.page_cap)
        return items[skip:skip + top]

    def _find(self, key):
        if key in self.issues:
            return self.issues[key]
        for i in self.issues.values():
            if i["idReadable"] == key:
                return i
        raise yb.Fail(f"GET /api/issues/{key} -> HTTP 404: not found")

    # -- the api() replacement ----------------------------------------------
    def api(self, method, path, params=None, body=None):
        params = params or {}
        fault = None
        if method != "GET":
            self.writes.append((method, path))
            for f in self.faults:
                if f["method"] == method and re.search(f["match"], path):
                    fault = f
                    self.faults.remove(f)
                    break
        if fault and fault["mode"] == "error-before":
            raise yb.Fail(f"{method} {path} -> HTTP 500: refused")
        result = None
        if not (fault and fault["mode"] == "noop"):
            result = self._route(method, path, params, body)
        if fault and fault["mode"] == "error-after":
            raise yb.Fail(f"curl failed (28): timed out after the server acted on {path}")
        return result

    def _route(self, method, path, params, body):
        if method == "GET" and path == "/api/admin/projects":
            return self._page(self.projects, params)
        if method == "GET" and path == "/api/issueLinkTypes":
            return self._page(LINK_TYPES, params)
        if method == "GET" and path == "/api/issues":
            short = params["query"].split(":", 1)[1].strip()
            found = sorted((i for i in self.issues.values() if i["project"] == short),
                           key=lambda i: yb.issue_number(i["idReadable"]))
            return self._page([self._render(i) for i in found], params)
        if method == "POST" and path == "/api/issues":
            short = next(p["shortName"] for p in self.projects if p["id"] == body["project"]["id"])
            number = 1 + max([yb.issue_number(i["idReadable"])[1]
                              for i in self.issues.values() if i["project"] == short] or [0])
            eid = self.add(f"{short}-{number}", body["summary"], status=None, type_=None)
            self._update(self.issues[eid], body)
            return {"id": eid, "idReadable": f"{short}-{number}"}
        m = re.fullmatch(r"/api/issues/([^/]+)/links/([^/]+)/issues(?:/([^/]+))?", path)
        if m:
            issue, link_id, child = self._find(m.group(1)), m.group(2), m.group(3)
            if method == "GET":
                return self._page([self._render(o) for o in self._linked(issue, link_id)], params)
            assert link_id == "L-3s", f"unexpected link write on {link_id}"
            if method == "POST":
                self._find(body["id"])["parent"] = issue["id"]   # YouTrack re-parents
                return {"id": body["id"]}
            if method == "DELETE":
                target = self._find(child)
                if target["parent"] == issue["id"]:
                    target["parent"] = None
                return None
        m = re.fullmatch(r"/api/issues/([^/]+)/(links|comments)", path)
        if m and method == "GET":
            issue = self._find(m.group(1))
            return self._page(self._links(issue) if m.group(2) == "links" else issue["comments"],
                              params)
        m = re.fullmatch(r"/api/issues/([^/]+)", path)
        if m and method == "GET":
            return self._render(self._find(m.group(1)))
        if m and method == "POST":
            self._update(self._find(m.group(1)), body)
            return {"id": m.group(1)}
        raise AssertionError(f"FakeYouTrack has no route for {method} {path}")

    def _update(self, issue, body):
        if "description" in body:
            issue["description"] = body["description"]
        for f in body.get("customFields", []):
            name = f["id"].removeprefix("F-")
            assert f["$type"] == PROTOS[name][1], f"wrong $type for {name}"
            value = f["value"]
            issue["fields"][name] = (value.get("name") or value.get("login")
                                     if isinstance(value, dict) else value)


class Base(unittest.TestCase):
    def setUp(self):
        self.yt = FakeYouTrack()
        self._api, self._sleep = yb.api, yb.time.sleep
        yb.api = self.yt.api
        yb.time.sleep = lambda _s: None
        self.tmp = tempfile.TemporaryDirectory()
        self.journal = os.path.join(self.tmp.name, "run.journal.jsonl")

    def tearDown(self):
        yb.api, yb.time.sleep = self._api, self._sleep
        self.tmp.cleanup()

    def collect(self, deep=True):
        return yb.collect(yb.resolve_project("GLASS"), deep=deep)

    def plan(self, snap, order=None, **top):
        order = order or snap["analysis"]["eligible"]
        items = [{"issue": rid, "rank": n, "readiness": "ready", "blockers": "",
                  "reason": f"reason for {rid}"} for n, rid in enumerate(order, 1)]
        if snap["epic_candidates"]:
            epic = {"action": "update", "idReadable": snap["epic_candidates"][0]["idReadable"]}
        else:
            epic = {"action": "create", "status": "Backlog", "approval": "Kevin, in session"}
        plan = {"project": "GLASS", "snapshot_collected_at": snap["collected_at"],
                "epic": epic, "items": items, "next_actionable": order[:1]}
        plan.update(top)
        return plan

    def item(self, plan, rid):
        return next(i for i in plan["items"] if i["issue"] == rid)

    def run_apply(self, snap, plan, dry_run=False):
        return yb.apply(snap, plan, self.journal, dry_run)

    def journal_ops(self):
        if not os.path.exists(self.journal):
            return []
        with open(self.journal, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh]

    def field_writes(self):
        return [w for w in self.yt.writes if re.fullmatch(r"/api/issues/3-\d+", w[1])]


class Pagination(Base):
    def test_short_pages_never_end_the_read(self):
        self.yt.page_cap = 3
        for n in range(1, 8):
            self.yt.add(f"GLASS-{n}", comments=[f"c{k}" for k in range(5)])
        snap = self.collect()
        self.assertEqual(len(snap["issues"]), 7)
        self.assertEqual(len(snap["issues"][0]["comments"]), 5)

    def test_a_stalled_pager_is_an_error_not_a_silent_stop(self):
        self.yt.add("GLASS-1")
        self.yt.stall = True
        with self.assertRaisesRegex(yb.Fail, "pager stalled"):
            self.collect()


class Eligibility(Base):
    def test_status_decides_and_the_resolved_flag_does_not(self):
        self.yt.add("GLASS-1", status="Done", resolved=None)        # Category veto: unresolved
        self.yt.add("GLASS-2", status="Wont do", resolved=None)     # not a resolved state
        self.yt.add("GLASS-3", status="In Progress", resolved=123)  # flag says resolved
        self.yt.add("GLASS-4", status="BLOCKED")
        self.yt.add("GLASS-5", status="Consider")
        self.yt.add("GLASS-6", status=None)
        snap = self.collect()
        self.assertEqual(snap["analysis"]["eligible"], ["GLASS-3", "GLASS-4", "GLASS-5"])
        self.assertEqual(snap["analysis"]["status_unknown"], ["GLASS-6"])
        self.assertEqual(snap["status_mapping"]["excluded"], ["Done", "Wont do"])
        self.assertEqual(snap["analysis"]["resolved_flag_disagrees"],
                         ["GLASS-1", "GLASS-2", "GLASS-3"])

    def test_every_do_not_do_spelling_present_is_excluded(self):
        mapping = yb.status_mapping(["Backlog", "Done", "Won't do", "Don't do"])
        self.assertEqual(mapping["do_not_do"], ["Won't do", "Don't do"])
        self.assertEqual(yb.status_class("Don't do", mapping), "do-not-do")

    def test_the_epic_is_not_evaluated(self):
        self.yt.add("GLASS-1")
        self.yt.add("GLASS-2", summary="GLASS-backlog-refinement", type_="Epic")
        snap = self.collect()
        self.assertEqual(snap["analysis"]["eligible"], ["GLASS-1"])
        self.assertEqual(snap["analysis"]["epic_state"], "one")

    def test_status_field_must_be_the_real_status(self):
        self.yt.add("GLASS-1")
        self.yt.status_proto = "157-33"   # a different field wearing the name
        with self.assertRaisesRegex(yb.Fail, "prototype 157-33"):
            self.collect()

    def test_an_unreadable_comment_stream_is_a_gap_not_an_empty_list(self):
        self.yt.add("GLASS-1", comments=["one"])
        real = self.yt.api

        def flaky(method, path, params=None, body=None):
            if path.endswith("/comments"):
                raise yb.Fail("GET comments -> HTTP 403")
            return real(method, path, params, body)
        yb.api = flaky
        snap = self.collect()
        self.assertIsNone(snap["issues"][0]["comments"])
        self.assertEqual(snap["gaps"][0]["what"], "comments")


class Projects(Base):
    def test_short_name_or_exact_name_resolves_to_one_project(self):
        self.assertEqual(yb.resolve_project("glass")["id"], "0-1")
        self.assertEqual(yb.resolve_project("Glass house")["shortName"], "GLASS")
        self.assertEqual(yb.resolve_project(
            "https://youtrack.kevininscoe.com/projects/GLASSY")["id"], "0-3")

    def test_ambiguous_name_is_refused_and_lists_the_candidates(self):
        with self.assertRaisesRegex(yb.Fail, r"Candidates: GLASS \(Glass house\), GLASSY"):
            yb.resolve_project("glas")

    def test_unknown_name_is_refused(self):
        with self.assertRaisesRegex(yb.Fail, "Candidates: none"):
            yb.resolve_project("nope")

    def test_template_project_is_refused(self):
        with self.assertRaisesRegex(yb.Fail, "template project"):
            yb.resolve_project("TMPL")


class Dependencies(Base):
    def test_cross_project_blocker_is_listed_with_its_status(self):
        self.yt.add("GLASS-1")
        self.yt.add("OTHER-1", status="In Progress")
        self.yt.add("OTHER-2", status="Wont do")
        self.yt.depend("GLASS-1", "OTHER-1")
        self.yt.depend("GLASS-1", "OTHER-2")
        blockers = {b["depends_on"]: b for b in self.collect()["analysis"]["cross_project_blockers"]}
        self.assertEqual(blockers["OTHER-1"]["blocker_status"], "In Progress")
        self.assertEqual(blockers["OTHER-1"]["blocker_project"], "OTHER")
        self.assertIn("alternative or a scope change", blockers["OTHER-2"]["note"])

    def test_relates_to_is_not_a_dependency(self):
        self.yt.add("GLASS-1")
        self.yt.add("GLASS-2")
        self.yt.relate("GLASS-1", "GLASS-2")
        snap = self.collect()
        self.assertEqual(snap["analysis"]["dependencies"], [])
        self.assertEqual(snap["issues"][0]["links"][0]["type"], "Relates")

    def test_prerequisite_must_rank_first(self):
        self.yt.add("GLASS-1")
        self.yt.add("GLASS-2")
        self.yt.depend("GLASS-1", "GLASS-2")
        snap = self.collect()
        self.assertIn("GLASS-1 is ranked before its prerequisite GLASS-2",
                      yb.validate_plan(snap, self.plan(snap)))
        self.assertEqual(yb.validate_plan(snap, self.plan(snap, ["GLASS-2", "GLASS-1"])), [])

    def test_a_prerequisite_the_agent_confirmed_from_prose_is_ordered_too(self):
        self.yt.add("GLASS-1")
        self.yt.add("GLASS-2")
        snap = self.collect()
        plan = self.plan(snap)
        self.item(plan, "GLASS-1")["after"] = ["GLASS-2"]
        self.assertIn("GLASS-1 is ranked before its prerequisite GLASS-2",
                      yb.validate_plan(snap, plan))

    def test_a_cycle_is_reported_and_no_order_is_invented(self):
        for n in (1, 2, 3):
            self.yt.add(f"GLASS-{n}")
        self.yt.depend("GLASS-1", "GLASS-2")
        self.yt.depend("GLASS-2", "GLASS-1")
        snap = self.collect()
        self.assertEqual(snap["analysis"]["cycles"], [["GLASS-1", "GLASS-2"]])
        plan = self.plan(snap)
        problems = yb.validate_plan(snap, plan)
        self.assertTrue(any("GLASS-1: in a dependency cycle" in p for p in problems))
        self.assertFalse(any("ranked before" in p for p in problems))
        for rid in ("GLASS-1", "GLASS-2"):
            self.item(plan, rid)["readiness"] = "needs-clarification"
        self.assertEqual(yb.validate_plan(snap, plan), [])


class PlanRules(Base):
    def setUp(self):
        super().setUp()
        for n in (1, 2, 3):
            self.yt.add(f"GLASS-{n}")
        self.snap = self.collect()

    def test_every_eligible_ticket_needs_exactly_one_rank(self):
        plan = self.plan(self.snap, ["GLASS-1", "GLASS-2"])
        self.assertIn("GLASS-3: eligible but has no rank", yb.validate_plan(self.snap, plan))
        plan = self.plan(self.snap)
        plan["items"][2]["rank"] = 2
        self.assertIn("ranks must be 1..3 with no gap or tie", yb.validate_plan(self.snap, plan))

    def test_an_approved_change_needs_an_approval_record_and_a_live_value(self):
        plan = self.plan(self.snap)
        self.item(plan, "GLASS-1")["priority"] = {"proposed": "Major", "decision": "approved"}
        self.item(plan, "GLASS-2")["priority"] = {"proposed": "Urgent", "decision": "pending"}
        self.item(plan, "GLASS-3")["affected_host"] = {"proposed": "saturn", "decision": "pending"}
        problems = yb.validate_plan(self.snap, plan)
        self.assertIn("GLASS-1: Priority is approved with no approval record", problems)
        self.assertIn("GLASS-2: Priority proposed 'Urgent' is not a live allowed value", problems)
        self.assertIn("GLASS-3: Affected host proposed 'saturn' is not a live allowed value",
                      problems)

    def test_a_field_is_never_cleared(self):
        plan = self.plan(self.snap)
        self.item(plan, "GLASS-1")["affected_host"] = {"proposed": None, "decision": "approved",
                                                      "approval": "Kevin"}
        self.assertTrue(any("never clears a field" in p
                            for p in yb.validate_plan(self.snap, plan)))

    def test_silence_is_not_approval(self):
        plan = self.plan(self.snap)
        self.item(plan, "GLASS-1")["priority"] = {"proposed": "Major"}   # no decision recorded
        self.assertTrue(any("marked unchanged but proposes" in p
                            for p in yb.validate_plan(self.snap, plan)))

    def test_a_plan_from_another_snapshot_is_refused(self):
        plan = self.plan(self.snap)
        plan["snapshot_collected_at"] = "earlier"
        with self.assertRaisesRegex(yb.Fail, "not made from this snapshot"):
            self.run_apply(self.snap, plan)
        self.assertEqual(self.yt.writes, [])


class Section(unittest.TestCase):
    SECTION = f"{yb.BEGIN_LINE}\n\nbody\n\n{yb.END_MARK}"

    def test_append_keeps_the_human_text(self):
        out = yb.splice_section("My own notes.\n\nSecond paragraph.", self.SECTION)
        self.assertTrue(out.startswith("My own notes.\n\nSecond paragraph.\n\n" + yb.BEGIN_PREFIX))

    def test_replace_touches_only_the_section(self):
        before = f"Above.\n\n{yb.BEGIN_PREFIX} old\nold body\n{yb.END_MARK}\n\nBelow."
        out = yb.splice_section(before, self.SECTION)
        self.assertEqual(out, f"Above.\n\n{self.SECTION}\n\nBelow.")
        self.assertEqual(yb.outside_section(out), yb.outside_section(before))
        self.assertEqual(out.count(yb.BEGIN_PREFIX), 1)

    def test_malformed_or_duplicate_markers_are_rejected(self):
        one = f"{yb.BEGIN_PREFIX} x\nbody\n{yb.END_MARK}"
        for bad in (one + "\n" + one,                       # two sections
                    f"{yb.BEGIN_PREFIX} x\nbody",           # never closed
                    f"body\n{yb.END_MARK}",                 # never opened
                    f"{yb.END_MARK}\n{yb.BEGIN_PREFIX} x"):  # wrong order
            with self.assertRaisesRegex(yb.Fail, "generated-section markers"):
                yb.splice_section(bad, self.SECTION)

    def test_empty_description_gets_the_section_alone(self):
        self.assertEqual(yb.splice_section("", self.SECTION), self.SECTION)


class Apply(Base):
    def setUp(self):
        super().setUp()
        self.yt.add("GLASS-1")
        self.yt.add("GLASS-2", host="FLDW")
        self.yt.add("GLASS-3")
        self.yt.add("GLASS-4", status="Done")

    def test_nothing_is_written_while_collecting_or_validating(self):
        snap = self.collect()
        yb.validate_plan(snap, self.plan(snap))
        yb.review_table(snap, self.plan(snap))
        self.assertEqual(self.yt.writes, [])

    def test_dry_run_writes_nothing(self):
        snap = self.collect()
        plan = self.plan(snap)
        self.item(plan, "GLASS-1")["priority"] = {"proposed": "Major", "decision": "approved",
                                                 "approval": "Kevin"}
        report = self.run_apply(snap, plan, dry_run=True)
        self.assertEqual(self.yt.writes, [])
        self.assertFalse(os.path.exists(self.journal))
        self.assertEqual(report["field_changes"], ["GLASS-1 Priority -> Major"])
        self.assertEqual(report["children_added"], ["GLASS-1", "GLASS-2", "GLASS-3"])

    def test_first_run_creates_one_epic_and_links_every_eligible_ticket(self):
        snap = self.collect()
        report = self.run_apply(snap, self.plan(snap))
        self.assertTrue(report["complete"], report)
        epic = self.yt.get(report["epic"])
        self.assertEqual(epic["summary"], "GLASS-backlog-refinement")
        self.assertEqual(epic["fields"]["Type"], "Epic")
        self.assertEqual(epic["fields"]["Status"], "Backlog")
        self.assertNotEqual(epic["fields"]["Date time entered"], 1)
        self.assertEqual(self.yt.children(report["epic"]), ["GLASS-1", "GLASS-2", "GLASS-3"])
        self.assertEqual(report["epic_url"],
                         f"https://youtrack.kevininscoe.com/issue/{report['epic']}")
        self.assertIn("| 1 | [GLASS-1](https://youtrack.kevininscoe.com/issue/GLASS-1)",
                      epic["description"])
        self.assertIn("Children added this run (verified): 3", epic["description"])

    def test_partial_field_approval_writes_only_what_was_approved(self):
        snap = self.collect()
        plan = self.plan(snap)
        self.item(plan, "GLASS-1")["priority"] = {"proposed": "Major", "decision": "approved",
                                                 "approval": "batch 1, Kevin"}
        self.item(plan, "GLASS-2")["priority"] = {"proposed": "Critical", "decision": "rejected"}
        self.item(plan, "GLASS-3")["priority"] = {"proposed": "Minor", "decision": "pending"}
        self.item(plan, "GLASS-1")["affected_host"] = {
            "proposed": "core", "approved_value": "web1", "decision": "approved",
            "approval": "amended by Kevin"}
        report = self.run_apply(snap, plan)
        self.assertEqual(self.yt.get("GLASS-1")["fields"]["Priority"], "Major")
        self.assertEqual(self.yt.get("GLASS-1")["fields"]["Affected host"], "web1")
        self.assertEqual(self.yt.get("GLASS-2")["fields"]["Priority"], "Normal")
        self.assertEqual(self.yt.get("GLASS-3")["fields"]["Priority"], "Normal")
        self.assertEqual(self.yt.get("GLASS-2")["fields"]["Affected host"], "FLDW")
        self.assertEqual(report["pending_decisions"], ["GLASS-3 Priority"])
        description = self.yt.get(report["epic"])["description"]
        self.assertIn("Normal (proposed: Minor, pending)", description)
        self.assertNotIn("Critical", description)
        # Status and Assignee of reviewed tickets are never touched.
        self.assertEqual(self.yt.get("GLASS-1")["fields"]["Status"], "Backlog")
        self.assertIsNone(self.yt.get("GLASS-1")["fields"]["Assignee"])

    def test_unchanged_rerun_reuses_the_epic_and_repeats_nothing(self):
        snap = self.collect()
        plan = self.plan(snap)
        self.item(plan, "GLASS-1")["priority"] = {"proposed": "Major", "decision": "approved",
                                                 "approval": "Kevin"}
        first = self.run_apply(snap, plan)
        epic = self.yt.get(first["epic"])
        epic["description"] = "Kevin's own notes.\n\n" + epic["description"] + "\n\nFooter."
        self.yt.writes.clear()

        snap2 = self.collect()
        self.assertEqual(snap2["epic_candidates"][0]["previous_ranks"],
                         {"GLASS-1": 1, "GLASS-2": 2, "GLASS-3": 3})
        plan2 = self.plan(snap2)
        self.item(plan2, "GLASS-1")["priority"] = {"proposed": "Major", "decision": "approved",
                                                  "approval": "Kevin"}
        second = self.run_apply(snap2, plan2)
        self.assertEqual(second["epic"], first["epic"])
        self.assertEqual(second["field_changes"], [])
        self.assertEqual(second["children_added"], [])
        self.assertEqual(len([i for i in self.yt.issues.values()
                              if i["summary"] == "GLASS-backlog-refinement"]), 1)
        # The only write is the description, replaced in place.
        self.assertEqual([w[0] for w in self.yt.writes], ["POST"])
        description = epic["description"]
        self.assertEqual(description.count(yb.BEGIN_PREFIX), 1)
        self.assertTrue(description.startswith("Kevin's own notes.\n\n"))
        self.assertTrue(description.endswith("\n\nFooter."))

    def test_closed_children_are_unlinked_and_not_deleted(self):
        snap = self.collect()
        first = self.run_apply(snap, self.plan(snap))
        self.yt.get("GLASS-2")["fields"]["Status"] = "Wont do"
        self.yt.get("GLASS-3")["fields"]["Status"] = "Done"
        self.yt.add("GLASS-9", status="Consider")            # new work since the last run
        snap2 = self.collect()
        report = self.run_apply(snap2, self.plan(snap2))
        self.assertEqual(report["children_removed"], ["GLASS-2", "GLASS-3"])
        self.assertEqual(report["children_added"], ["GLASS-9"])
        self.assertEqual(self.yt.children(first["epic"]), ["GLASS-1", "GLASS-9"])
        self.assertIn("GLASS-2", [i["idReadable"] for i in self.yt.issues.values()])
        self.assertNotIn("[GLASS-2]", self.yt.get(first["epic"])["description"])

    def test_cross_project_child_is_removed_only_with_approval(self):
        snap = self.collect()
        first = self.run_apply(snap, self.plan(snap))
        self.yt.add("OTHER-5", parent=first["epic"])
        snap2 = self.collect()
        plan = self.plan(snap2)
        self.assertTrue(any("OTHER-5 is a child of the epic" in p
                            for p in yb.validate_plan(snap2, plan)))
        plan["membership_removals"] = [{"issue": "OTHER-5", "decision": "pending"}]
        report = self.run_apply(snap2, plan)
        self.assertIn("OTHER-5", self.yt.children(first["epic"]))
        self.assertTrue(any("OTHER-5" in s for s in report["skipped"]))
        snap3 = self.collect()
        plan = self.plan(snap3, membership_removals=[{"issue": "OTHER-5", "decision": "approved",
                                                     "approval": "Kevin"}])
        self.run_apply(snap3, plan)
        self.assertNotIn("OTHER-5", self.yt.children(first["epic"]))


class ParentConflicts(Base):
    def setUp(self):
        super().setUp()
        self.yt.add("GLASS-1")
        self.yt.add("GLASS-2", summary="An existing parent", type_="Epic")
        self.yt.add("GLASS-3", parent="GLASS-2")

    def test_a_conflict_needs_a_recorded_decision(self):
        snap = self.collect()
        self.assertEqual(snap["analysis"]["parent_conflicts"],
                         [{"issue": "GLASS-3", "parent": "GLASS-2", "parent_project": "GLASS"}])
        self.assertTrue(any("must record replace or keep" in p
                            for p in yb.validate_plan(snap, self.plan(snap))))

    def test_keep_leaves_the_parent_and_reports_incomplete_membership(self):
        snap = self.collect()
        plan = self.plan(snap)
        self.item(plan, "GLASS-3")["parent"] = {"decision": "keep"}
        report = self.run_apply(snap, plan)
        self.assertEqual(self.yt.get("GLASS-3")["parent"], self.yt.eid("GLASS-2"))
        self.assertEqual(report["membership_incomplete"], {"GLASS-3": "existing parent GLASS-2"})
        self.assertFalse(report["complete"])
        self.assertIn("not a child of this epic: existing parent GLASS-2",
                      self.yt.get(report["epic"])["description"])

    def test_replace_needs_approval_and_then_reparents(self):
        snap = self.collect()
        plan = self.plan(snap)
        self.item(plan, "GLASS-3")["parent"] = {"decision": "replace"}
        self.assertTrue(any("replacing its parent has no approval record" in p
                            for p in yb.validate_plan(snap, plan)))
        self.item(plan, "GLASS-3")["parent"]["approval"] = "Kevin"
        report = self.run_apply(snap, plan)
        self.assertEqual(self.yt.get("GLASS-3")["parent"], self.yt.eid(report["epic"]))

    def test_a_link_that_would_make_a_cycle_is_never_written(self):
        self.yt.add("GLASS-4", summary="GLASS-backlog-refinement", type_="Epic", parent="GLASS-1")
        snap = self.collect()
        plan = self.plan(snap)
        self.item(plan, "GLASS-3")["parent"] = {"decision": "keep"}
        report = self.run_apply(snap, plan)
        self.assertEqual(report["membership_incomplete"]["GLASS-1"],
                         "would create a hierarchy cycle")
        self.assertIsNone(self.yt.get("GLASS-1")["parent"])
        self.assertNotIn("GLASS-4", snap["analysis"]["eligible"])


class Epics(Base):
    def setUp(self):
        super().setUp()
        self.yt.add("GLASS-1")

    def test_duplicate_epics_need_a_human_choice_and_no_third_is_created(self):
        self.yt.add("GLASS-2", summary="GLASS-backlog-refinement", type_="Epic")
        self.yt.add("GLASS-3", summary="GLASS-backlog-refinement", type_="Epic")
        snap = self.collect()
        self.assertEqual(snap["analysis"]["epic_state"], "multiple")
        plan = self.plan(snap)
        plan["epic"] = {"action": "create", "status": "Backlog", "approval": "Kevin"}
        self.assertTrue(any("name one of: GLASS-2, GLASS-3" in p
                            for p in yb.validate_plan(snap, plan)))
        plan["epic"] = {"action": "update", "idReadable": "GLASS-3"}
        self.assertTrue(any("choosing GLASS-3 has no approval record" in p
                            for p in yb.validate_plan(snap, plan)))
        plan["epic"]["canonical_approval"] = "Kevin chose GLASS-3"
        report = self.run_apply(snap, plan)
        self.assertEqual(report["epic"], "GLASS-3")
        self.assertEqual(self.yt.children("GLASS-3"), ["GLASS-1"])
        self.assertEqual(len(self.yt.issues), 3)

    def test_a_wrong_type_or_closed_epic_is_corrected_only_with_approval(self):
        self.yt.add("GLASS-2", summary="GLASS-backlog-refinement", type_="Task", status="Done")
        snap = self.collect()
        plan = self.plan(snap)
        problems = yb.validate_plan(snap, plan)
        self.assertTrue(any("has Type 'Task', not Epic" in p for p in problems))
        self.assertTrue(any("has Status 'Done'" in p for p in problems))
        plan["epic"]["corrections"] = {"type": {"approval": "Kevin"},
                                       "status": {"to": "Backlog", "approval": "Kevin"}}
        report = self.run_apply(snap, plan)
        self.assertEqual(report["epic"], "GLASS-2")
        self.assertEqual(self.yt.get("GLASS-2")["fields"]["Type"], "Epic")
        self.assertEqual(self.yt.get("GLASS-2")["fields"]["Status"], "Backlog")

    def test_malformed_markers_stop_the_plan_before_any_write(self):
        self.yt.add("GLASS-2", summary="GLASS-backlog-refinement", type_="Epic",
                    description=f"{yb.BEGIN_PREFIX} a\n{yb.BEGIN_PREFIX} b\n{yb.END_MARK}")
        snap = self.collect()
        with self.assertRaisesRegex(yb.Fail, "generated-section markers"):
            self.run_apply(snap, self.plan(snap))
        self.assertEqual(self.yt.writes, [])

    def test_create_that_errors_after_landing_is_adopted_not_repeated(self):
        self.yt.faults.append({"method": "POST", "match": r"^/api/issues$", "mode": "error-after"})
        snap = self.collect()
        report = self.run_apply(snap, self.plan(snap))
        epics = [i for i in self.yt.issues.values() if i["summary"] == "GLASS-backlog-refinement"]
        self.assertEqual(len(epics), 1)
        self.assertEqual(report["epic"], epics[0]["idReadable"])
        self.assertEqual(self.journal_ops()[0]["outcome"], "applied-verified-after-error")
        self.assertEqual(self.yt.children(report["epic"]), ["GLASS-1"])

    def test_create_that_really_failed_is_reported_and_not_retried(self):
        self.yt.faults.append({"method": "POST", "match": r"^/api/issues$", "mode": "error-before"})
        snap = self.collect()
        report = self.run_apply(snap, self.plan(snap))
        self.assertIsNone(report["epic"])
        self.assertFalse(report["complete"])
        self.assertEqual(len(self.yt.issues), 1)
        self.assertEqual(len([w for w in self.yt.writes if w == ("POST", "/api/issues")]), 1)
        self.assertEqual(report["failures"][0]["op"], "create-epic")

    def test_an_epic_that_appeared_since_the_review_blocks_a_second_create(self):
        snap = self.collect()
        plan = self.plan(snap)
        self.yt.add("GLASS-2", summary="GLASS-backlog-refinement", type_="Epic")
        report = self.run_apply(snap, plan)
        self.assertEqual(len(self.yt.issues), 2)
        self.assertTrue(report["epic_blocked"])
        self.assertTrue(report["description"].startswith("blocked"))


class Recheck(Base):
    def setUp(self):
        super().setUp()
        for n in (1, 2, 3):
            self.yt.add(f"GLASS-{n}")
        self.snap = self.collect()
        self.plan_ = self.plan(self.snap)
        for rid in ("GLASS-1", "GLASS-2"):
            self.item(self.plan_, rid)["priority"] = {"proposed": "Major", "decision": "approved",
                                                     "approval": "Kevin"}

    def test_a_ticket_that_changed_since_review_is_left_alone(self):
        self.yt.get("GLASS-1")["fields"]["Priority"] = "Critical"   # someone else moved it
        report = self.run_apply(self.snap, self.plan_)
        self.assertEqual(self.yt.get("GLASS-1")["fields"]["Priority"], "Critical")
        self.assertEqual(self.yt.get("GLASS-2")["fields"]["Priority"], "Major")
        self.assertEqual(report["drift"]["issues"],
                         {"GLASS-1": ["Priority changed 'Normal' -> 'Critical'"]})
        self.assertEqual(report["membership_incomplete"], {"GLASS-1": "changed since review"})
        self.assertTrue(report["description"].startswith("blocked"))
        self.assertFalse(report["complete"])
        self.assertEqual(self.yt.get(report["epic"])["description"], "")

    def test_status_and_parent_changes_are_drift(self):
        self.yt.get("GLASS-2")["fields"]["Status"] = "Done"
        self.yt.add("GLASS-7", summary="Someone's parent")
        self.yt.get("GLASS-3")["parent"] = self.yt.eid("GLASS-7")
        drift = yb.compute_drift(self.snap, self.collect(deep=False), self.plan_)
        self.assertEqual(drift["issues"]["GLASS-2"], ["Status changed 'Backlog' -> 'Done'"])
        self.assertEqual(drift["issues"]["GLASS-3"], ["parent changed"])
        self.assertEqual(drift["issues"]["GLASS-7"], ["new eligible ticket, not reviewed"])

    def test_a_new_ticket_blocks_only_the_description(self):
        self.yt.add("GLASS-8")
        report = self.run_apply(self.snap, self.plan_)
        self.assertEqual(report["field_changes"],
                         ["GLASS-1 Priority -> Major", "GLASS-2 Priority -> Major"])
        self.assertEqual(self.yt.children(report["epic"]), ["GLASS-1", "GLASS-2", "GLASS-3"])
        self.assertTrue(report["description"].startswith("blocked"))


class Retries(Base):
    def setUp(self):
        super().setUp()
        self.yt.add("GLASS-1")
        self.yt.add("GLASS-2", summary="GLASS-backlog-refinement", type_="Epic")
        self.snap = self.collect()
        self.plan_ = self.plan(self.snap)
        self.item(self.plan_, "GLASS-1")["priority"] = {
            "proposed": "Major", "decision": "approved", "approval": "Kevin"}
        self.field_path = f"^/api/issues/{self.yt.eid('GLASS-1')}$"

    def test_an_error_after_the_write_landed_is_verified_not_repeated(self):
        self.yt.faults.append({"method": "POST", "match": self.field_path, "mode": "error-after"})
        report = self.run_apply(self.snap, self.plan_)
        self.assertEqual(self.yt.get("GLASS-1")["fields"]["Priority"], "Major")
        self.assertEqual(report["field_changes"], ["GLASS-1 Priority -> Major"])
        self.assertEqual(len([w for w in self.field_writes()
                              if w[1] == self.field_path.strip("^$")]), 1)
        self.assertEqual(report["failures"], [])

    def test_a_200_that_changed_nothing_is_a_failure(self):
        self.yt.faults.append({"method": "POST", "match": self.field_path, "mode": "noop"})
        report = self.run_apply(self.snap, self.plan_)
        self.assertEqual(self.yt.get("GLASS-1")["fields"]["Priority"], "Normal")
        self.assertEqual(report["failures"][0]["error"], "read-back does not match")
        self.assertFalse(report["complete"])

    def test_a_link_write_that_did_nothing_is_reported(self):
        self.yt.faults.append({"method": "POST", "match": r"/links/L-3s/issues$", "mode": "noop"})
        report = self.run_apply(self.snap, self.plan_)
        self.assertEqual(report["membership_incomplete"], {"GLASS-1": "link write failed"})
        self.assertEqual(report["children_added"], [])

    def test_a_rerun_after_a_partial_failure_finishes_the_rest(self):
        self.yt.faults.append({"method": "POST", "match": r"/links/L-3s/issues$",
                               "mode": "error-before"})
        first = self.run_apply(self.snap, self.plan_)
        self.assertFalse(first["complete"])
        self.yt.writes.clear()
        snap = self.collect()      # the journal is not trusted: live state is read again
        plan = self.plan(snap)
        self.item(plan, "GLASS-1")["priority"] = {"proposed": "Major", "decision": "approved",
                                                 "approval": "Kevin"}
        second = self.run_apply(snap, plan)
        self.assertTrue(second["complete"], second)
        self.assertEqual(second["field_changes"], [])          # already in place, not rewritten
        self.assertEqual(second["children_added"], ["GLASS-1"])
        self.assertEqual(self.field_writes(), [("POST", f"/api/issues/{self.yt.eid('GLASS-2')}")])


class Tables(Base):
    def test_review_table_covers_every_ticket_in_batches_with_full_urls(self):
        for n in range(1, 8):
            self.yt.add(f"GLASS-{n}", summary=f"Pipe | in summary {n}")
        snap = self.collect()
        plan = self.plan(snap)
        self.item(plan, "GLASS-2")["priority"] = {"proposed": "Major", "decision": "pending"}
        table = yb.review_table(snap, plan, batch_size=3)
        self.assertEqual(table.count("Batch "), 3)
        for n in range(1, 8):
            self.assertIn(f"https://youtrack.kevininscoe.com/issue/GLASS-{n} ", table)
        self.assertIn("Normal → Major [pending]", table)
        self.assertIn("Normal (no change)", table)
        self.assertIn("Pipe \\| in summary 1", table)
        self.assertIn("none existing match for \"GLASS-backlog-refinement\"", table)


class Wrapper(unittest.TestCase):
    def test_shell_wrapper_parses_and_uses_the_broker(self):
        path = os.path.join(HERE, "yt-backlog")
        self.assertEqual(subprocess.run(["bash", "-n", path]).returncode, 0)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("parzival exec --as ai youtrack-claude-code", text)
        for banned in ("parzival get", "bao kv get", "bao-breakglass", "app/YouTrack"):
            self.assertNotIn(banned, text)

    def test_api_refuses_to_run_outside_the_broker(self):
        env = {k: v for k, v in os.environ.items() if k != "YOUTRACK_CURL_CONFIG"}
        proc = subprocess.run([sys.executable, os.path.join(HERE, "yt_backlog.py"),
                               "resolve-project", "GLASS"], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("YOUTRACK_CURL_CONFIG is not set", proc.stderr)


if __name__ == "__main__":
    unittest.main()
