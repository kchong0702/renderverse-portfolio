---
version: "1.0"
description: "ParentHandoffMiddleware's instruction to a child agent on what to do with a message outside its scope"
author: "kchong0702"
date: "2026-11-25"
status: "active"
---

When a message is outside your scope, call `handoff_to_parent` and write nothing else. The agent that handed you the conversation answers it.
