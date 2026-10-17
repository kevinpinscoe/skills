---
name: skill-directory-name
category: category-slug
description: One sentence describing what this skill does.
disable-model-invocation: true
---

# <Skill Name>

> One sentence describing what this skill does.

_The `##` sections below are required (Parameters and Notes optional) and stay in this order.
A skill may add its own `##` sections between them where it needs them:_

- _**Before Prerequisites** — scope or orientation the reader must take in first (e.g. `Scope`)_
- _**Before Instructions** — reference material the steps rely on (e.g. `Background`, naming rules)_
- _**After Instructions, before Success Criteria** — rules that apply while executing (e.g. `Guardrails`)_

_Delete this note and the list above from the finished skill._

## Prerequisites

- List any tools, access, credentials, or system state required
- e.g. `aws` CLI configured with profile `default`
- e.g. Target directory must exist

## Parameters

| Name | Description | Default |
|------|-------------|---------|
| `PARAM` | What it controls | `value` |
| `REQUIRED_PARAM` | What it controls | _(required — ask the user)_ |

_Omit this section if the skill takes no parameters._

## Instructions

1. **Step label** — describe what to do and how (be explicit; include exact commands or MCP calls).
2. **Step label** — if condition Z, then do W; otherwise do X.
3. **Report** — output results as: ...

## Success Criteria

- What "done" looks like
- e.g. Output shows "backup verified" and exit code is 0

## Notes

- Edge cases, known limitations, or related skills
- e.g. Run this skill before `restore-from-backup`
