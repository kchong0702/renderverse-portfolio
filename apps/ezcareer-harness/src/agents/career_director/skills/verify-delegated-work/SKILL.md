---
name: verify-delegated-work
description: Check what a workflow tool or subagent returned before telling the user about it.
---

# Verify delegated work

The workflows already check their own output in code: citations quote the posting, changesets pass validation and fit the page, and fit scores are computed. Don't check those again. Check what code can't:

1. It did what the user asked. A changeset changes the part they named. An analysis is of the posting they gave.
2. It changed nothing they didn't ask for. Each edit's path names a part their request covers.
3. Your reply claims nothing the report doesn't say. Give fit scores as they came back, and never estimate one.

When a check fails, say what is wrong in one sentence and ask whether to try again.
