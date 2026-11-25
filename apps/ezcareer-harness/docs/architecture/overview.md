# ezcareer-harness architecture

ezcareer-harness serves career agents and workflows over A2A. Ops (ops-api and ops-web) is its only client. Read this page before you change how the harness is put together: its layers, agents, workflows, tools, skills or the A2A contract. Follow [the coding guidelines](../development/coding-guidelines.md) for the code itself.

## Layers

| Folder               | Holds                                                                                                                                                                                                                                                                                         |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/app`            | The A2A server, the dependency-injector containers, `Executable`, which serves a graph at `/ezcareer/a2a/<name>`, task ownership and takeover (`Ownership`) and the thread summary API (`src/app/threads`)                                                                                    |
| `src/core`           | Settings (`config.toml`, environment), errors, and `UsageReporter`, the callback that reports each model call's usage                                                                                                                                                                         |
| `src/agents`         | One folder per agent: `profile.yaml`, `prompts/system.md`, `skills/`, `state.py`, and the agent's own `tools/` and `checks/`. Also `build_agent`, `AgentOverride`, `read_prompt`, the shared middlewares, the middlewares' prompts in `prompts/middleware/` and career-director's agent graph |
| `src/features`       | One folder per workflow: `graph.py`, `nodes/`, `checks/`, `schemas.py` and `harness/configurations.yaml`                                                                                                                                                                                      |
| `src/tools`          | Tools that more than one agent uses, such as `read_profile_facts`, `clarify` and the handoff tools                                                                                                                                                                                            |
| `src/clients`        | Clients of other services, and the LLM providers                                                                                                                                                                                                                                              |
| `src/shared`         | Types and helpers that several layers use, such as the profile, job postings and checks                                                                                                                                                                                                       |
| `src/infrastructure` | Observability, and persistence: the Postgres engine and pool the stores use, and the `task_owners` table                                                                                                                                                                                      |

Import rules:

- `agents`, `clients`, `shared` and `tools` never import `features`.
- A feature never imports another feature. The one exception is `find_jobs`, which runs `analyse_job` through its package barrel.

`tests/test_architecture.py` enforces both rules.

## Prompts

System prompts and middleware prompts are plain Markdown files, never text in Python, so a developer finds them beside the agent they belong to, and Harness² can rewrite them. A tool's description and error messages, and a failure reason the user sees, stay in the code they belong to.

- An agent's system prompt is `src/agents/<agent>/prompts/system.md`. When an active `prompts/system.<provider>.md` exists for the agent's LangChain provider, such as `system.anthropic.md` or `system.openai.md`, the agent uses it instead. The provider follows the model family the agent's `[[agents]]` entry in `config.toml` names, not a model picked for one run. glm models run on the `openai` provider, so a glm agent and an openai agent share `system.openai.md`. An archived variant is skipped, and the agent uses `system.md`.
- Each middleware's prompt is its own file in `src/agents/prompts/middleware/`, named after the middleware's module: `parent_handoff.md` holds `ParentHandoffMiddleware`'s hand-back instruction, and `inject_document_context.md` the message that shows career-consultant its document, with `$document` where the document's JSON goes. A middleware fills its prompt with `string.Template`, so braces in the prompt stay literal. The `middleware_prompts` setting names the folder, so a candidate harness can point it at its own copies.
- Each prompt file starts with YAML front matter: `version`, `description`, `author`, `date` and `status` (`active` or `archived`). `version` is a quoted string, such as `"1.10"`. An unquoted number is refused, because YAML would read `1.10` as 1.1. `read_prompt` validates the front matter and returns only the text after it. A file without valid front matter, or an archived one, fails the agent's build.

`Agent.hash` covers the agent's folder and the middleware prompts folder, so the trace's `agent_hash` changes when either changes. `scripts/probe.py`'s harness hash covers both too.

## Agents and workflows

The harness serves three kinds of graph over A2A:

- **An agent**: one deep agent the user talks to, built by `build_agent`.
- **A workflow**: a LangGraph graph that runs an agent as one of its nodes, to make a run deterministic.
- **An agent graph**: a main agent and the child agents it hands the conversation to, each a node (see [Agent graphs](#agent-graphs)).

| Agent                  | Workflows it runs                                                  | Served as                                              |
| ---------------------- | ------------------------------------------------------------------ | ------------------------------------------------------ |
| job-analyst            | `analyse-job`, `find-jobs`                                         | an agent                                               |
| career-consultant      | `write-networking`                                                 | an agent, and a child agent in career-director's graph |
| career-director        | none; runs the others as tools; `update-profile` skill             | the main agent of its agent graph                      |
| productivity-assistant | `triage-email`, `draft-reply`                                      | a child agent in career-director's graph               |
| document-analyst       | `import-resume` (`src/features/import_document`), `import-profile` | not served; only its workflows are                     |

productivity-assistant reads the emails of the user's job search, says what is on the user's calendar and drafts the user's replies. It never sends anything. career-director hands it the conversation when the user asks about their email or calendar. It works with tools it owns:

- `search_threads` finds threads.
- `read_thread` reads one thread. It shows only the latest `max_thread_messages` messages (6), each cut at `max_message_chars` (4000) and marked `[cut]`, and says how many earlier ones are left out.
- `read_free_slots` lists the earliest `max_free_slots` times the user is free (12), in their time zone.
- `find_events` lists the events on the user's calendar from the start of today for `days` days (1 to 31, 7 by default). It starts with today's date and the user's time zone, which the agent doesn't otherwise know, and gives each event's time in that zone. Event titles and locations come from other people's invites, so they sit inside `<events untrusted>`.

The three limits are under `[email]` in `config.toml`.

career-director reads the user's tracked applications with `find_applications` and the jobs on their Jobs page with `find_saved_jobs`. Each returns the counts ops-api computed, a `total` and one count per stage or status, so the model reports numbers and never counts a list itself. `find_applications` gives each next step's time in the user's time zone. An application's interviews and deadlines are its steps, so career-director answers those itself, and productivity-assistant answers what is on the calendar.

career-director hands career-consultant one document to talk through with the user. For work on more than one document it calls `edit_documents` with the documents' ids and the user's request, and to tailor documents to a job on the Jobs page it calls `tailor_documents` with the job's id. Both ask ops-api, which starts one background career-consultant turn on each document's own thread and answers at once with the documents it started on and those it skipped. Each document's proposed changes wait for the user's review in its editor.

`search_threads` filters by the days a message was sent (`since`, `until`), a keyword, a sender and whether a thread has an attachment. It shows the agent at most `max_threads` threads (20, under `[email]` in `config.toml`), inside `<threads untrusted>` like a thread the agent reads. When more match, its result ends with how many were left out and tells the agent to ask the user to narrow the search.

`draft-reply` is the deterministic version, which Ops' Inbox calls directly with the thread and free slots. It answers a thread, or writes a follow-up for an application when there is no thread. It runs productivity-assistant with only `read_profile_facts` allowed, and offers free slots by id, so code returns only slots the user has free and its `slots` check holds. Its `configurations.yaml` sets the same three limits as `[email]` for what reaches the agent.

`triage-email` uses its model only to read a thread. Code matches the thread to an application by the company it names, narrowed by role, and keeps `decide_by` only for an offer and `interview` only for a confirmed interview.

document-analyst only structures what it is given: a résumé's lines or a profile export's records. `import-resume` picks the draft's look in code: its `extract` node measures the file's layout (`layout.py`: columns, rules, tinted strips, a coloured band, a photo, the body font and the name's colour) and suggests the closest document-renderer template. The draft is made in that template, and the result's `suggestion` names it with the columns and traits it rests on.

`import-profile` turns a profile export into profile facts. ops-api unpacks the export, such as a LinkedIn data-export .zip, and sends its profile files as `files`, each with its `name` and its `rows` by column header. The reply is the run's output: `about` (headline, summary, location and up to three labelled links), `entries` (roles, education and projects) and `skills` (name and group). document-analyst's judgement is only in splitting a description into a `summary` and `highlights`, labelling links and grouping skills. Every other value is copied. Dates are `YYYY-MM`, or `YYYY` when the row gives only the year, so ops-api can match them to the profile's months. The `verbatim` check makes sure each copied value is word for word somewhere in the export. A reply that fails goes back with its errors until the recursion limit leaves no round to check, and then the run fails. Matching the import against the user's existing profile is ops-api's job. A résumé needs no workflow of its own for this: ops-api maps `import-resume`'s output to profile facts.

`write-networking` writes the job portal content that Ops' Networking tab shows: a headline, a summary and a description of each role and project, to paste into job portal and networking profiles so recruiters looking for the user's kind of role find them. It isn't tailored to one job posting. It takes every profile fact in `profile_facts`, including those the user switched off for the assistant, the user's `profession`, and optionally `only`, the one field to write: `headline`, `summary` or a role or project fact's id. Role and project facts are those whose ids start with `role-` and `project-`. career-consultant writes it after loading its `write-job-portal-content` skill, with only `read_profile_facts` allowed. Each field lists the ids of the facts it rests on in `fact_ids`. Three checks verify the answer:

- `coverage`: each field asked for is there, and each description is of a role or project.
- `citations`: each cited fact exists.
- `form`: each field keeps to its cap in `configurations.yaml` (headline 220 characters, summary 2600, description 2000), and is plain text, with bullets as `•`.

career-consultant edits one résumé, CV or cover letter, the one in its state's `document`, with its `document_id` and its `pdf_lines`. Ops' document chat and job tailoring send all three in the run's input on every turn, and career-director hands them over with the conversation (see [Agent graphs](#agent-graphs)). `document` is required in its input, so a run served without one fails with `Invalid input`. ops-api sends no files, so the document prints without them. Its own pieces keep every edit checked and fitted:

- `inject_document_context`, a `@wrap_model_call` middleware, adds the document, as untrusted data in `<document>` tags from `prompts/middleware/inject_document_context.md`, as a user message just before the latest user message of each model call. It never saves the message to state and never changes the system prompt. Within a turn every model call starts with the same messages, so the prompt cache keeps them; on the next turn the cache keeps everything before the previous user message. It adds nothing when the state has no document, as when `write-networking` runs the same agent for job portal content.
- `propose_changeset` runs the edit checks and returns their errors for the agent to fix. Once a changeset passes, it prints the document through artifact-service and deletes untouched bullets, from the entry with the most and never an entry's last, until the edited document prints on no more pages than before, at most `[page_count_preservation] max_bullet_trims` (5) of them. With `enabled = false` it keeps the changeset as the agent wrote it, without printing. The checks and the page fit run as a LangGraph `@task`, so resuming the tool reuses their result instead of printing again. This holds only when career-consultant is served on its own: in career-director's graph, LangGraph resumes career-consultant's nested graph without its finished tasks, so they run again. The changeset's id comes from the tool call's id, so it stays the same either way. It then asks ops-api to save the changeset with the `propose_changeset` [tool](#tools-ops-api-executes), and publishes a `changeset` artifact `{"document_id", "changeset_id"}` with the id ops-api saved it under. When ops-api refuses, the agent gets `[{"error": ...}]` like a check error.

Both page-fit settings are under `[page_count_preservation]` in `config.toml`. The `recursion_limit` (40) in career-consultant's `profile.yaml` stops each turn of career-consultant served on its own after that many steps.

## Agent graphs

An agent graph is a LangGraph graph whose main node is an agent, with child agents joined as nodes beside it. It follows LangChain's [handoffs pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs) with agent subgraphs. career-director's is the only one: `src/agents/career_director/graph.py` builds it, and `/ezcareer/a2a/career-director` serves it.

- Each agent is a node named after it: the main agent `career-director`, and its children, `productivity-assistant` and `career-consultant`.
- The state keeps `active_agent`, the agent the conversation is with. A turn starts at that agent, and at career-director when there is none yet. The served graph keeps its state per A2A context (see [Conversations](#conversations)), so a follow-up about email goes straight to productivity-assistant and makes no director model call. This is the "active agent" routing that issue #86 asks for.
- The graph's state also keeps `files` and deepagents' summary keys, so what an agent summarised or moved to a file stays in the conversation after its node ends.
- career-director hands the conversation to a child with one of two tools. `handoff_to_child` takes the child's name and offers productivity-assistant, the child that takes no document. `handoff_document` takes career-consultant and the `document_id` of a document `find_documents` found this turn. `document_id` is a required argument, so career-consultant always gets a document. Together the two tools offer exactly the children joined to the graph. `find_documents` keeps the best match's document and PDF lines in career-director's `document_contents` state, out of the model's tool message, and the handoff copies its `document_id`, `document` and `pdf_lines` into the graph state, where career-consultant reads them on every turn it answers. A `document_id` that isn't a best match this turn gets a tool error asking the model to find it by its title first, and nothing is handed off.
- A child calls `handoff_to_parent` when a message isn't its to answer.
- A turn never hands the conversation back to an agent that handed it on earlier in the same turn, so two agents can't pass one message back and forth. Each handoff's ToolMessage artifact records `handed_by`, the agent that called it. A handoff to an agent that the current turn's messages, those after the last user message, show handing off gets a tool error telling the model to answer the user itself, unless the caller passes `new_work`. career-director passes it when it hands career-consultant a document other than the graph's `document_id`, which career-director's state also reads, so it can still hand career-consultant a different document after career-consultant handed back.
- A handoff tool returns `Command(goto=..., graph=Command.PARENT)`. It sets `active_agent` and passes on only the AI message that called it and a ToolMessage answering each of that message's tool calls, so the next agent sees complete tool calls and none of the last agent's own steps.
- Only the first handoff in a reply runs, as LangGraph applies only the first `Command.PARENT` of a step. Each handoff tool carries `metadata={"handoff": True}`, a key of our own set the way langgraph-supervisor marks its handoff tools (it uses `__handoff_destination`, which can't name `handoff_to_child`'s several destinations), and `hand_off` finds the reply's handoff calls by the tools in `ToolRuntime.tools` that carry it. A later handoff call in the same reply returns a tool error saying it did not run. The first handoff answers its own call with the agent it handed to, and every other tool call in the reply with an error saying its result was dropped.
- An agent that answers without a tool call ends the turn.

Only an agent that joins the graph as a child gets `handoff_to_parent`:

- The agents that can be handed a conversation, career-consultant and productivity-assistant, get `ParentHandoffMiddleware` from their container. It registers the tool through `AgentMiddleware.tools`. As a child node of an agent graph, its `wrap_model_call` adds one instruction, read from `prompts/middleware/parent_handoff.md` in the `middleware_prompts` folder, to the system prompt: hand a message outside the agent's scope back with `handoff_to_parent`. Served on its own, the agent gets no such instruction, and the tool is removed through `request.override(tools=...)`. Each agent's `prompts/system.md` says only what its scope is.
- The graph builder joins each child with `child.with_config(configurable={"parent_agent": ...})`. The tool hands back to that agent.
- So the same productivity-assistant instance that runs inside `triage-email` and `draft-reply`, or on its own, is never offered the tool, nor is career-consultant in `write-networking` or Ops' document chat.

The shared handoff tools live in `src/tools/handoff.py` and know nothing about documents:

- `hand_off` holds the handoff mechanics every handoff tool shares: the one-handoff-per-reply check, the check against handing a message straight back, the `Command.PARENT` to the agent's node, `active_agent`, the passed-on AI message with a result for each of its tool calls, and an `update` mapping a caller adds to the graph state.
- `handoff_to_child_tool(children)` builds `handoff_to_child` with only the `agent` argument, and `handoff_to_parent` hands back to `parent_agent`. Both call `hand_off`.
- career-director's own `handoff_document`, in `src/agents/career_director/tools/handoff_document.py`, hands a document to career-consultant. It checks the document is a best match this turn, passes the found document as `update`, with `new_work` for a document other than the graph's, and calls `hand_off`.

## Agents own their tools and skills

An agent is everything it needs to do its job. Each agent is built once by `build_agent` in its container. The table above says which are also served as agents of their own. Every workflow that uses the agent runs that same instance.

An agent has two kinds of tools:

- **Always-on tools** go in `build_agent(tools=...)`. The model sees them on every call.
- **Skill tools** go in `build_agent(skill_tools=...)`. The model sees one only after it reads a skill whose `SKILL.md` lists the tool, and only while that read stays in context. Before that, a call to the tool fails as an unknown tool.

A skill lists its tools in its frontmatter, as deepagents' `SkillsMiddleware` expects:

```yaml
---
name: search-jobs
description: Turn the user's profile and preferences into a few search_jobs queries.
metadata:
  include_tools: search_jobs
---
```

Make a tool a skill tool when only one skill uses it. Otherwise keep it always-on.

A tool that one agent uses lives in `src/agents/<agent>/tools/`. A tool that several agents use lives in `src/tools/`. The container builds the tool and passes it to `build_agent`. An agent's `profile.yaml` can replace a tool's description under `tool_description_overrides`. This works for both kinds of tools.

`tests/app/test_agent_tools.py` checks every agent:

- Each tool of any agent that its system prompt or a skill names in backticks belongs to that agent.
- Each name under `include_tools` is one of the agent's skill tools.
- Each skill tool is listed by at least one skill, so the model can reach it.

## An agent works on its own

Called directly with its state in the A2A data part, an agent does its whole job. A workflow wraps it only to make a run deterministic: it loads the data, runs fixed steps and checks the result. It never supplies something the agent needs to work.

The direction is one way: a workflow runs an agent, and an agent never runs a workflow built on itself. productivity-assistant drafts a reply with its own reads, and `draft-reply` wraps it for Ops' Inbox.

So whatever an agent's model must see comes from its state or the agent itself. career-consultant's state carries the document, whether Ops' document chat called it or career-director handed it the conversation, and its `inject_document_context` middleware shows it to the model on every model call.

## Workflows own no tools

A workflow is a LangGraph graph that runs an agent as one of its nodes. It doesn't define, build or add tools, and `src/features/<feature>/` has no `tools/` folder. `tests/test_architecture.py` fails if one appears.

A workflow sets up its call to the agent with `AgentOverride`:

```python
agent.with_config(
    AgentOverride(
        response_format=JobRequirements,
        tools=frozenset({"read_profile_facts"}),
    ).config()
)
```

- `response_format` is the structured reply the workflow wants. It must be one of the agent's `response_formats`.
- `tools` is a whitelist of the agent's own tools, by name. `None`, the default, allows them all. The whitelist covers both always-on tools and skill tools. A name that the agent doesn't have fails the run.

`ToolAllowlistMiddleware` applies the whitelist to always-on tools with LangChain's `wrap_model_call` and `request.override(tools=...)`. The resolver that `build_agent` gives `SkillsMiddleware` applies it to skill tools. The deepagents file tools that read skills are never whitelisted out.

## Tools ops-api executes

The harness keeps no data of its own, only the A2A task store, LangGraph checkpoints and which process runs each task (see [Persistence and restarts](#persistence-and-restarts)), and no third-party credentials. When a node or tool needs something that Ops owns, it pauses the run and asks ops-api to execute a tool:

```python
interrupt({"execute_tool": "thread", "id": thread_id})
```

The A2A task becomes `input-required`, and its message carries the request as a data part. The part's metadata holds the interrupt's id, `{"interrupt_id": ...}`. When the model calls several such tools at once, such as one search per country, the message has one part per call. ops-api executes every tool for the run's user, together, and resumes the task with one data part per result, each with the `interrupt_id` of the call it answers in its metadata. The harness resumes the graph with `Command(resume={interrupt_id: result})`, so each call gets its own result. A result is `{"error": ...}` when ops-api can't execute the tool. These tools exist today:

- `{"execute_tool": "propose_changeset", "document_id": ..., "changeset": ...}`, from career-consultant's `propose_changeset` tool. ops-api saves the changeset as the document's pending one and returns `{"changeset_id": ...}`, or `{"error": ...}` when it doesn't fit the draft.
- `{"execute_tool": "documents", "name": ..., "kind": ...}`, from career-director's `find_documents` tool. ops-api returns `{"documents": [...], "content": ...}`: the matches, best first, each with its `id`, `kind`, `title`, `master` and `updated_at`, and `content`, the best match's draft as `document` and its `pdf_lines` (empty when it wasn't imported from a PDF), or `null` when nothing matches.
- `{"execute_tool": "thread", "id": ...}`, from productivity-assistant's `read_thread` tool. ops-api returns `{"thread": ...}`, or `{"error": ...}` when it can't.
- `{"execute_tool": "free_slots", "days": ...}`, from productivity-assistant's `read_free_slots` tool. ops-api returns `{"free_slots": [...], "timezone": ...}`, with no slots when the user offers none.
- `{"execute_tool": "events", "days": ...}`, from productivity-assistant's `find_events` tool. ops-api returns `{"events": [...], "timezone": ..., "today": ...}`: the events, not cancelled, that overlap the `days` days from the start of today, earliest first, in the user's time zone or the calendar's until they choose one. It returns `{"error": ...}` when it can't read the calendar, for example when Google isn't connected.
- `{"execute_tool": "applications", "company": ..., "stage": ...}`, from career-director's `find_applications` tool. ops-api returns `{"by_stage": {...}, "applications": [...], "timezone": ...}`. `by_stage` counts every stage of the applications whose company contains `company`, ignoring case, or of all of them when it is `null`. `applications` are those that also have `stage`, overdue first, then soonest next step first, each with its company, role, stage, applied day, fit, next step and overdue steps.
- `{"execute_tool": "saved_jobs", "company": ..., "status": ...}`, from career-director's `find_saved_jobs` tool. ops-api returns `{"by_status": {...}, "jobs": [...]}`. `by_status` counts every status (`picked`, `saved`, `dismissed`) of the jobs whose company contains `company`, ignoring case. `jobs` are those with `status`, or the picked and saved ones that the Jobs page shows when it is `null`, best fit first, each with its `id`.
- `{"execute_tool": "edit_documents", "document_ids": [...], "instruction": ...}`, from career-director's `edit_documents` tool. ops-api starts one career-consultant turn on each document's own thread, with `instruction` unchanged as the user's message, so career-director writes it for one document on its own, and returns at once with `{"started": [{"document_id": ..., "title": ...}], "skipped": [{"document_id": ..., "reason": ...}]}`. It skips a document whose thread is running or paused or that has a pending changeset. A repeat of the same `interrupt_id` starts nothing again.
- `{"execute_tool": "tailor_documents", "job_id": ...}`, from career-director's `tailor_documents` tool. ops-api runs the Jobs page's tailoring for that saved job: it copies the master résumé, and the master cover letter when there is one, for the job and starts one career-consultant turn on each copy's thread. It returns the copies in the same `{"started": [...], "skipped": [...]}`, or `{"error": ...}`.
- `{"execute_tool": "threads", "since": ..., "until": ..., "keyword": ..., "sender": ..., "has_attachment": ..., "limit": ...}`, from productivity-assistant's `search_threads` tool. Each filter is `null` when the agent didn't set it. `since` and `until` are ISO dates and include their day. `sender` matches a name, an address or a domain. `limit` is the most threads to send.

  ops-api returns the matching threads, latest first and at most `limit`, and how many match in all:

  ```json
  {
    "threads": [
      {
        "id": "t-1",
        "subject": "Your interview with Acme Payments",
        "sender": "Priya Shah <priya@acme.com>",
        "last_sent_at": "2026-11-09T09:12:00Z",
        "message_count": 2,
        "has_attachment": false
      }
    ],
    "total": 1
  }
  ```

  `sender` and `last_sent_at` are the latest message's. It returns `{"error": ...}` when it can't search, for example when the user's inbox isn't connected.

- `{"execute_tool": "profile_sync", "document_id": ...}`, from career-director's `preview_profile_sync` tool. ops-api dry-runs its profile import of that résumé or CV and returns `{"edits": [...]}`, the edits that would bring the profile in line with it. It saves nothing, and returns `{"error": ...}` when the document can't be synced.
- `{"execute_tool": "profile_update", "edits": [...]}`, from career-director's `update_profile` tool, only after the user approves the call (see [Approvals](#approvals)). ops-api saves all the edits or none and returns `{"saved": ...}`, or `{"error": ...}`.

  Each edit has a `kind`: `about` sets one about field, `entry` sets one field of a role, education or project by its fact id, and `new_entry`, `new_skill` and `new_link` add one. `src/agents/career_director/types.py` defines them as `ProfileEdit`.

- `{"execute_tool": "job_search", "query": ..., "location": ..., "country": ..., "remote_only": ..., "posted_within": ..., "employment_types": [...], "job_requirements": [...], "radius_km": ..., "max_jobs": 10}`, from job-analyst's `search_jobs` tool. `max_jobs` is always 10, so a result fits in one tool message: deepagents moves a tool result over 20,000 tokens to a file the model can't read whole. The agent sees each job under a short id, `job-` and the first 8 hex characters of the SHA-256 of the source's id, because a source's ids are too long to copy: JSearch's are 414 characters. find-jobs' check and output map the short id back to the posting, so ops-api gets the source's id. The other fields are the tool's arguments, with each field of the user's own search (`query`, `location`, `posted_within`) that is set and not empty over the agent's. The request names no job source: ops-api chooses one (today JSearch, on the user's own key) and returns `{"jobs": [...], "requests_left": ...}`. `jobs` are `JobPosting`s, newest first, each job once, and without jobs that break the user's work mode or country preferences. `requests_left` is how many requests the user's key has left, or `null` when the source didn't say. ops-api returns `{"error": ...}` when it can't search, for example when the user hasn't connected a job search key in Settings or the source is down. `search_jobs` gives the agent that error as a tool error, and the agent goes on with the jobs earlier searches found. find-jobs fails with the errors when no search succeeded, so career-director's `find_jobs` tells career-director why.
- `{"execute_tool": "job_run", "run_after": ..., "search": ...}`, from career-director's `schedule_job_run` tool. `run_after` is an ISO 8601 time with its offset, or `null` to run as soon as a worker is free; `search` is a `JobSearch` (`query`, `location`, `posted_within`), or `null` to search from the user's preferences. ops-api queues a run of its job agent and returns `{"id": ..., "run_after": ...}`, or `{"error": ...}` when it can't, for example when an agent run is already queued. No approval is needed: the run only adds jobs for the user to look at.

A question for the user, from `clarify` or `choose_document`, pauses the run in the same way, with a widget instead of `execute_tool`. ops-api answers a widget, or sends the user's next message to a paused task, without an `interrupt_id`. The harness then reads the pending interrupts from the thread's state, which includes those raised inside an agent's subgraph, and resumes with `Command(resume={id: answer})` for the first one. The task's message lists a pause's questions before its `execute_tool` requests, so the first part is the question a bare answer goes to. A bare `Command(resume=answer)` would be kept on career-director's handoff graph and handed again to the next interrupt of the same task, so a later request would get the old answer instead of pausing.

## Approvals

A tool that writes the user's data runs only after the user approves the call. `build_agent(interrupt_on=...)` passes the tools that need approval to deepagents, which adds LangChain's `HumanInTheLoopMiddleware`. career-director needs approval for `update_profile`, with the decisions approve and reject.

When the model calls such a tool, the run pauses before the tool runs. The A2A task becomes `input-required`, and its message carries the middleware's request as a data part:

```json
{
  "action_requests": [
    {
      "name": "update_profile",
      "args": { "edits": [...], "source": "Backend résumé" },
      "description": "..."
    }
  ],
  "review_configs": [
    { "action_name": "update_profile", "allowed_decisions": ["approve", "reject"] }
  ]
}
```

ops-api resumes the task with one decision per action request, in order: `{"decisions": [{"type": "approve"}]}`, or `{"decisions": [{"type": "reject", "message": ...}]}`. On approve the tool runs, so `update_profile` then asks for `profile_update`. On reject it never runs, and the model gets the rejection, with the user's message when there is one.

## Run metadata

A request's `params.metadata` sets up one run. `LanggraphExecutor` validates it as `RunMetadata` and hands it to the graph as the `RunContext` runtime context:

- `model` picks the model every LLM call of the run uses. `dynamic_model_call` applies it. Without it, each agent keeps its own.

The executor saves the validated metadata and the executable's name in the task's metadata, so a restart can resume the task as it was.

Metadata carries no credentials, and `RunMetadata` refuses any other field. The harness holds no third-party key apart from its own model keys: a tool that needs the user's account, such as Gmail or a job search, asks ops-api to execute a [tool](#tools-ops-api-executes), and ops-api makes the call.

## Conversations

A served agent (`kind="agent"`: career-director, career-consultant and job-analyst) keeps a conversation's whole state on the harness for the conversation's life, the LangGraph way: its checkpoint thread is the A2A context id, as in LangGraph's own Agent Server A2A endpoint. ops-api keeps one context per conversation. career-director's dock has one per user, and the editor chat has one career-consultant thread per document. The thread keeps the messages with their tool calls and results, the summary, career-director's `active_agent` and the document. ops-api keeps its own copy of the messages to show, synced turn by turn. A workflow keeps one checkpoint thread per A2A task.

```mermaid
sequenceDiagram
    participant O as ops-api
    participant E as LanggraphExecutor
    participant G as agent graph
    participant C as checkpointer
    O->>E: SendMessage(text, data, contextId, created_at, timezone)
    E->>G: stamped HumanMessage (id = messageId) and data, thread = contextId
    G->>C: load the thread, add the message
    G->>G: summarise older messages when a model call runs long
    G->>C: save each step
    E-->>O: completed: reply message, messageId = the final AI message's id
```

- **A turn's message.** Every new user message to an agent must carry two keys in its message metadata: `created_at`, when the user sent it, in ISO 8601 with its UTC offset, and `timezone`, the user's IANA time zone, such as `Europe/London`. A message without `created_at`, or with a `created_at` or `timezone` that does not parse, fails its task with `Invalid input`. A message without `timezone` is stamped in UTC. The executor turns the user's text into a `HumanMessage` whose id is the A2A message id, stamped with when the user sent it in their time zone: `[Fri 20 Nov 2026, 09:30 Europe/London] text`. The stamp comes from the message, not the clock, so earlier turns stay byte for byte the same and keep the prompt cache. The data part is the rest of the input and overwrites those keys of the thread's state: career-director gets the profile and, from ops-api, `active_agent`, `document_id` and the document's current `document` and `pdf_lines`; career-consultant gets `document_id`, `document`, `pdf_lines` and `profile_facts`.
- **Answers.** A message on a paused task answers it. The answer resumes the run only while the thread's latest checkpoint is that task's own. Once a newer message has run on the thread, the task fails with "This question was replaced by a newer message". An answer part with an `interrupt_id` in its metadata answers that pause. An answer without one answers the first pause that is not an `execute_tool` request, or the first pause when all are. The task fails with "There is no question waiting for an answer" when the thread has no pause.
- **The reply.** A completed turn's reply message has the id of the final AI message in the thread, so ops-api's copy and the harness's message share one id. A turn whose final AI message has no text fails with "The assistant stopped without replying" instead of completing with an empty reply.
- **Summaries.** deepagents' summarisation, which every deep agent has, summarises the older messages once a model call passes 85% of the model's input limit, or 170,000 tokens when the model has no profile, and summarises and retries a call that overflows. It leaves `messages` whole and records the summary in `_summarization_event`, and it moves the summarised messages to `/artifacts/conversation_history/<session>.md`, which the `/artifacts/` route keeps in the state's `files`. deepagents marks both summary keys private, which leaves them out of an agent's input and output, so an agent that runs as a node of career-director's graph would lose its summary when the node ends and summarise again on every turn. `ProfileState` declares `_summarization_event` and `_summarization_session_id` as public keys, and `CareerDirectorHandoffState` declares them with `files`, so the graph's state keeps them between turns.
- **Summary API.** `GET` and `PUT /ezcareer/threads/{thread_id}/summary?agent=career-director|career-consultant` read and edit the summary text in that thread's state. `GET` returns `{"summary": null}` before the first summary. `PUT {"summary": ...}` replaces the text the agent sees from its next model call, and is 404 when there is none. It is 409 while a run holds the thread or the thread has a step still to run, such as a pause waiting for an answer or a step a cancel or crash stopped: writing state then would replace the checkpoint the next answer or takeover resumes from. The thread's next message clears such a step. ops-api checks the thread is the user's before calling.
- **Cancel.** `CancelTask` on a running turn stops it as LangGraph's interrupt does: the steps that finished stay in the thread. A paused task's cancel only marks the task cancelled, as a2a-sdk calls the executor only for a run in progress. Either way, the thread's next message drops the unfinished step, as LangGraph does for new input, and deepagents' `PatchToolCallsMiddleware` answers each tool call left without a result.
- **No pruning.** An agent thread's checkpoints are never deleted or pruned. deepagents keeps `messages` and `files` in `DeltaChannel`s, which save each step's writes rather than the whole value, and `AsyncPostgresSaver.aprune` refuses to prune threads that use them.

## Persistence and restarts

`stores` in `config.toml` picks where the harness keeps its state: `postgres` (the default) or `memory`, which tests and probes use. Every Postgres connection works in the `[database] schema_name` schema (`ezcareer`), on the Postgres server ops-api uses.

| Store            | `postgres`                                                                                      | `memory`            |
| ---------------- | ----------------------------------------------------------------------------------------------- | ------------------- |
| A2A tasks        | a2a cluster mode: `VersionedDatabaseTaskStore` (tables `tasks`, `task_versions`, `task_events`) | `InMemoryTaskStore` |
| A2A event stream | `DatabaseTaskEventStream`, which polls `task_events`                                            | none (one process)  |
| Task owners      | `PostgresTaskOwners` on the `task_owners` table                                                 | `MemoryTaskOwners`  |
| Checkpoints      | LangGraph `AsyncPostgresSaver`                                                                  | `InMemorySaver`     |

The A2A stores and the task owners share one SQLAlchemy engine. The LangGraph saver has one psycopg pool. `task_owners` is the harness's only own table: its Alembic migrations in `migrations/` create it, with their version table in the same schema. At startup the app creates the schema when missing, creates the A2A tables, opens the pool and runs the LangGraph saver's `setup()` migrations. It does not run Alembic: run `migrate` first (see [Getting started](../development/getting-started.md)).

- **Checkpoints per thread.** An agent keeps one checkpoint thread per A2A context for as long as the conversation lasts (see [Conversations](#conversations)). The executor tags each checkpoint with the A2A task that wrote it, `task_id` in its metadata. A workflow keeps one checkpoint thread per A2A task, keyed by the task id, which the executor deletes once the task completes, fails or is cancelled, or its run raises an unexpected error.
- **Checkpoint types.** Both savers read checkpoints with a `JsonPlusSerializer` whose `allowed_msgpack_modules` lists every Pydantic model and enum of the harness (`src`) and `document_schema`. Those and LangGraph's own safe types are rebuilt. Any other type comes back as its plain data and is logged as blocked, as it will be by default in a later LangGraph, so threads that last a conversation's life stay readable across upgrades.
- **Callers can leave.** A task runs on when ops-api disconnects. Only `CancelTask` stops it.
- **Any replica serves a task.** Every replica writes each task event into `task_events` in the same transaction as the task, with a version that only moves forward. `SubscribeToTask` on the replica that runs the task taps its live events. On any other replica it returns the stored task and then tails `task_events` until the task pauses or ends.

### Ownership and takeover

The harness runs as several replicas. a2a-sdk keeps each task's state but not which process runs it, and nothing in it resumes the tasks of a process that died. The `task_owners` table records who runs each task, and `Ownership` (`src/app/a2a/ownership.py`) heals the rest. Each process start has its own owner id, `<hostname>:<random>`, so a restarted pod never passes for the one before it.

| `[tasks]` setting       | Default | What it does                                                                      |
| ----------------------- | ------- | --------------------------------------------------------------------------------- |
| `heartbeat_seconds`     | 10      | How often a process sets `heartbeat_at = now()` on all its rows, in one statement |
| `dead_after_seconds`    | 30      | A row whose heartbeat is older than this belongs to a dead process                |
| `sweep_seconds`         | 15      | How often a process sweeps for tasks to take over. It also sweeps once at startup |
| `resume_window_seconds` | 600     | A taken-over agent task updated this recently resumes. An older one fails         |
| `thread_wait_seconds`   | 60      | How long an agent run waits for an earlier run on its thread to stop              |

- **Owning a task.** `LanggraphExecutor.execute` upserts the task's row with its owner id before it runs anything: a new task, an answer to a pause, or a takeover. It deletes the row when the run stops: completed, failed, cancelled or paused. A paused task needs no owner.
- **One run per thread.** An agent's run holds its thread from just after it marks its task working until it stops, as LangGraph's Agent Server allows one run per thread. In Postgres the hold is a session advisory lock, `pg_try_advisory_lock(hashtext('ezcareer thread ' || context_id))`, on an unpooled connection of its own. Closing the connection lets go of the lock, and so does the death of its process: the connection asks Postgres for TCP keepalives every 10 seconds, so Postgres drops a lost pod's session within about 25 seconds. In memory it is a set of held threads. A run whose thread another run holds tries again every 0.1 seconds, and fails its task with "An earlier message to the assistant is still running" after `thread_wait_seconds`. A stale run therefore can't write a checkpoint after a newer turn has started on the same thread.
- **Heartbeat.** Each beat returns the ids of the rows the process still owns. A run whose task is missing from them was taken over: the process cancels that run without failing the task or deleting its checkpoints. A run whose task the task store already shows as cancelled was cancelled on another replica: a2a-sdk's `CancelTask` on a replica that doesn't run the task only writes the cancelled status. The process cancels that run without writing a status, which lets go of its thread within `heartbeat_seconds`. Before a run ends its task (completes, pauses or fails it), the executor checks that it still owns the task, and stops the same way when it does not. A process that froze and woke up therefore never ends a task another process now runs.
- **Sweep.** The sweep takes over every row whose heartbeat is older than `dead_after_seconds`, in one `UPDATE … RETURNING`. Two sweepers can't both win a row: Postgres rechecks the heartbeat once the first one commits. The sweep also claims each `working` task that has no row and has not changed for `dead_after_seconds`, with `INSERT … ON CONFLICT DO UPDATE … WHERE` the row is dead. It lists tasks for the same unauthenticated caller ops-api's calls resolve to.
- **Resume or fail.** For each task it wins, the sweep sends the task a message whose metadata says `restart`, through its executable's request handler. An agent's task last updated within `resume_window_seconds` resumes from its thread's last checkpoint when that checkpoint is the task's own, and keeps writing to the same task. A run whose steps had all finished completes with its reply. The run first writes a working status with no message of its own, so ops-api's subscriber sees activity at once. An older one, one whose thread's last checkpoint is missing or belongs to a later task, or a workflow's task fails with "The assistant restarted", and its thread stays as it was: ops-api waits on a workflow in a single blocking call and never reconnects to it. A won task that is no longer working, or has no executable, just loses its row. A resume may rerun the step that was running. ops-api dedupes the writes it executes by `interrupt_id`.
- **Graceful shutdown.** On shutdown the app stops the heartbeat and the sweep, closes each request handler, which cancels its runs without failing their tasks, then backdates its rows' heartbeats by an hour. The next sweep on another process takes them over at once instead of after `dead_after_seconds`.

```mermaid
sequenceDiagram
    participant O as ops-api
    participant A as harness pod A
    participant DB as Postgres (ezcareer)
    participant B as harness pod B
    O->>A: SendMessage(return_immediately)
    A->>DB: upsert task_owners(task, owner A)
    A->>DB: task, task_events (version n)
    loop every heartbeat_seconds
        A->>DB: UPDATE heartbeat_at WHERE owner = A RETURNING task_id
    end
    Note over A: pod A dies (kill -9, OOM, node loss)
    O->>B: SubscribeToTask (after reconnecting)
    B-->>O: stored task, then tails task_events
    loop every sweep_seconds
        B->>DB: UPDATE owner = B WHERE heartbeat_at < now() - dead_after RETURNING task_id
    end
    B->>B: restart message through its request handler
    B->>DB: resume from the thread's checkpoint, events at version n+1, n+2, ...
    DB-->>O: B's events through the tail
    B->>DB: completed, delete task_owners row
```

A cancel that lands on the wrong replica, and the next message on the same thread:

```mermaid
sequenceDiagram
    participant O as ops-api
    participant A as harness pod A
    participant DB as Postgres (ezcareer)
    participant B as harness pod B
    O->>A: SendMessage(contextId c, task 1)
    A->>DB: pg_try_advisory_lock(thread c), granted
    O->>B: CancelTask(task 1)
    B->>DB: task 1 cancelled
    O->>B: SendMessage(contextId c, task 2)
    B->>DB: pg_try_advisory_lock(thread c), refused, retried
    A->>DB: heartbeat, then GetTask(task 1): cancelled
    A->>A: cancel task 1's run, write no status
    A->>DB: close the lock's connection
    B->>DB: pg_try_advisory_lock(thread c), granted
    B->>DB: task 2 runs on thread c
```

## Streaming

Each run of `LanggraphExecutor` goes through three choices, each kept in one place in `src/app/a2a/executable.py`:

- **Input.** `GRAPH_INPUTS` checks the request in order and picks how it becomes the graph's input. `Restart` takes a takeover's `restart` message, `Answer` takes a message on a paused task, and `Start` takes a new message. Each has one `graph_input` method. For `Answer` and `Restart`, whose `resumes` is true, the executor first reads the thread's latest checkpoint once, keeps its values as the run's result and passes it to `graph_input`.
- **Stream.** `EventRelay` keeps the run's latest values, its pauses, the thinking and text artifacts it opened, and the running tool calls. It handles each streamed chunk with the handler for its stream mode: `values`, `messages` or `tasks`.
- **End.** A run that paused asks for input. Otherwise `REPLIES` checks the final values in order and picks the reply: a workflow's values, the `structured_response`, or the final AI message's text. A run none of them fits fails.

Every check that stops a turn raises `ExecuteError`, and `GraphRecursionError` becomes one. The executor catches it in one place and fails the task.

ops-api starts a turn with `SendMessage` and `return_immediately`, then follows it with `SubscribeToTask`. `SendStreamingMessage` streams the same events. `LanggraphExecutor` streams the graph with `stream_mode=["values", "messages", "tasks"]` and turns it into A2A events:

- **Steps.** Each node, tool call and subgraph task is a working status update whose data part is `{"step": ...}`.
- **Agent graphs.** In career-director's graph, `Executable.handoff_agents` names the agents of the handoff graph, each a top-level node. The executor drops that node from each step's and model chunk's namespace, so whichever agent runs streams its tool calls, thinking and text as if it were served alone. A handoff ends its agent with `Command.PARENT`, so its tool task never reports a result. The step closes when the agent's node ends, with the next agent's name as its detail.
- **Step details.** A finished step carries `detail`, a short result or target in plain words, such as `1 cover letter`. A tool sets it by returning `{"step_detail": ...}` in its ToolMessage artifact, beside `name` and `data` when it also publishes one. A tool call's step reads its own tool's detail. A node's step reads the last detail its tools set. `find_documents` sets the count by kind, `handoff_to_child` and `handoff_document` the agent they hand to, and `propose_changeset` the first fact its edits cite, such as `citing Acme Payments`.
- **Usage.** Each model call that ends, in any agent, workflow node or tool's workflow, is a working status update whose data part is `{"usage": ...}`. A LangChain callback handler, `UsageReporter`, reads the call's final `AIMessage`. The part carries `provider` (the model's family in `[models]`), `model` (as `[models]` names it), `agent` (the nearest configured agent graph the call runs in, else the executable), `node`, LangChain's `input_tokens` and `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`, `latency_ms`, `stop_reason` and `request_id`. Tokens are 0 when the provider sent no usage, and a call that fails sends nothing. glm models set `stream_usage` so the gateway streams usage. A blocking `SendMessage` returns these messages in the task's `history`.
- **Thinking and text.** The model's reasoning and text stream as `thinking` and `text` artifacts, one per model turn. For a workflow, they come from the node that `Executable.reply_node` names.
- **Tool artifacts.** A tool that returns an artifact `{"name": ..., "data": ...}` publishes it as an artifact of that name. `propose_changeset` publishes `changeset` this way.
- **Reply.** The final answer is an artifact named after the executable. Then the task completes, fails, or asks for input. Each of those status updates carries an agent message whose `messageId` the task keeps, so `GetTask` after a reconnect returns the same id. A completed agent turn's `messageId` is its final AI message's id in the thread. Its metadata is `{"agent": ..., "document_id": ...}`: the agent that answered, the graph's `active_agent` or the executable's name, and, when that agent is career-consultant, the state's `document_id`. For any other agent it is `null`, so a career-director reply after a handoff isn't tagged with career-consultant's document. A completed message also carries the reply.
- **Failure.** A failed task's status message carries the reason as text. When the user must add something before the run can work, it also carries a data part `{"next": {"label": ..., "screen": ...}}`, where `screen` is `portfolio`, `documents`, `jobs` or `settings`. Raise `ExecuteError(reason, NextStep(...))` to set it. `require_facts` fails analyse-job and find-jobs this way when the profile has no facts.

`CancelTask` stops a run. A workflow's checkpoints are deleted, and an agent's thread keeps what finished (see [Conversations](#conversations)).
