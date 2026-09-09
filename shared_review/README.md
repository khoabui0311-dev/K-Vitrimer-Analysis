# Shared correction review

This folder is the handoff point for agents and human reviewers working in this repository.
Read PLAN.md and WORK_LOG.md first, then VALIDATION.md when available. Source changes
remain in the working tree and can be inspected with `git diff`.

Reviewers: record recommendations in a separate Markdown file here, with severity,
file/line, reproducible evidence, and proposed acceptance test. Do not overwrite another
agent's log. Never put private experimental data or credentials in this folder.

This is a local project folder; no external service or network share is configured.

Latest implementation handoff: [Plateau and activation-energy batch](PLATEAU_BATCH.md).

Current whole-project review: [9 September 2026 audit](PROJECT_AUDIT.md), including
confirmed fixes, regression/export evidence and remaining release/scientific gaps.
