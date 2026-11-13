# ezcareer-harness architecture

ezcareer-harness serves career agents and workflows over A2A. Ops (ops-api and ops-web) is its only client. Read this page before you change how the harness is put together: its layers, agents, workflows, tools, skills or the A2A contract. Follow [the coding guidelines](../development/coding-guidelines.md) for the code itself.

## Layers

| Folder               | Holds                                                                                                                                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/app`            | The A2A server, the dependency-injector containers, and `Executable`, which serves a graph at `/ezcareer/a2a/<name>`                                                                                                |
| `src/core`           | Settings (`config.toml`, environment), errors, and `UsageReporter`, the callback that reports each model call's usage                                                                                               |
| `src/agents`         | One folder per agent: `profile.yaml`, `system.md`, `skills/`, `state.py`, and the agent's own `tools/` and `checks/`. Also `build_agent`, `AgentOverride`, the shared middlewares and career-director's agent graph |
| `src/features`       | One folder per workflow: `graph.py`, `nodes/`, `checks/`, `schemas.py` and `harness/configurations.yaml`                                                                                                            |
| `src/tools`          | Tools that more than one agent uses, such as `read_profile_facts`, `clarify` and the handoff tools                                                                                                                  |
| `src/clients`        | Clients of other services, and the LLM providers                                                                                                                                                                    |
| `src/shared`         | Types and helpers that several layers use, such as the profile, job postings and checks                                                                                                                             |
| `src/infrastructure` | Observability and persistence                                                                                                                                                                                       |

Import rules:

- `agents`, `clients`, `shared` and `tools` never import `features`.
- A feature never imports another feature. The one exception is `find_jobs`, which runs `analyse_job` through its package barrel.

`tests/test_architecture.py` enforces both rules.

## Agents and workflows

The harness serves three kinds of graph over A2A:

- **An agent**: one deep agent the user talks to, built by `build_agent`.
- **A workflow**: a LangGraph graph that runs an agent as one of its nodes, to make a run deterministic.
- **An agent graph**: a main agent and the child agents it hands the conversation to, each a node (see [Agent graphs](#agent-graphs)).

| Agent                  | Workflows it runs                                                   | Served as                                |
| ---------------------- | ------------------------------------------------------------------- | ---------------------------------------- |
| job-analyst            | `analyse-job`, `find-jobs`                                          | an agent                                 |
| career-consultant      | `edit-document` (`src/features/write_document`), `write-networking` | an agent                                 |
| career-director        | none; runs the others as tools; `update-profile` skill              | the main agent of its agent graph        |
| productivity-assistant | `triage-email`, `draft-reply`                                       | a child agent in career-director's graph |
| document-analyst       | `import-resume` (`src/features/import_document`), `import-profile`  | not served; only its workflows are       |

productivity-assistant reads the emails of the user's job search and drafts the user's replies. It never sends anything. career-director hands it the conversation when the user asks about their email. It drafts a reply itself, with tools it owns:

- `search_threads` finds threads.
- `read_thread` reads one thread. It shows only the latest `max_thread_messages` messages (6), each cut at `max_message_chars` (4000) and marked `[cut]`, and says how many earlier ones are left out.
- `read_free_slots` lists the earliest `max_free_slots` times the user is free (12), in their time zone.

These limits are under `[email]` in `config.toml`.

`search_threads` filters by the days a message was sent (`since`, `until`), a keyword, a sender and whether a thread has an attachment. It shows the agent at most `max_threads` threads (20, under `[email]` in `config.toml`), inside `<threads untrusted>` like a thread the agent reads. When more match, its result ends with how many were left out and tells the agent to ask the user to narrow the search.

`draft-reply` is the deterministic version, which Ops' Inbox calls directly with the thread and free slots. It answers a thread, or writes a follow-up for an application when there is no thread. It runs productivity-assistant with only `read_profile_facts` allowed, and offers free slots by id, so code returns only slots the user has free and its `slots` check holds. Its `configurations.yaml` sets the same three limits as `[email]` for what reaches the agent.

`triage-email` uses its model only to read a thread. Code matches the thread to an application by the company it names, narrowed by role, and keeps `decide_by` only for an offer and `interview` only for a confirmed interview.

document-analyst only structures what it is given: a résumé's lines or a profile export's records. `import-resume` picks the draft's look in code: its `extract` node measures the file's layout (`layout.py`: columns, rules, tinted strips, a coloured band, a photo, the body font and the name's colour) and suggests the closest document-renderer template. The draft is made in that template, and the result's `suggestion` names it with the columns and traits it rests on.

`import-profile` turns a profile export into profile facts. ops-api unpacks the export, such as a LinkedIn data-export .zip, and sends its profile files as `files`, each with its `name` and its `rows` by column header. The reply is the run's output: `about` (headline, summary, location and up to three labelled links), `entries` (roles, education and projects) and `skills` (name and group). document-analyst's judgement is only in splitting a description into a `summary` and `highlights`, labelling links and grouping skills. Every other value is copied. Dates are `YYYY-MM`, or `YYYY` when the row gives only the year, so ops-api can match them to the profile's months. The `verbatim` check makes sure each copied value is word for word somewhere in the export. A reply that fails goes back with its errors until the recursion limit leaves no round to check, and then the run fails. Matching the import against the user's existing profile is ops-api's job. A résumé needs no workflow of its own for this: ops-api maps `import-resume`'s output to profile facts.

`write-networking` writes the job portal content that Ops' Networking tab shows: a headline, a summary and a description of each role and project, to paste into job portal and networking profiles so recruiters looking for the user's kind of role find them. It isn't tailored to one job posting. It takes every profile fact, including those the user switched off for the assistant, the user's `profession`, and optionally `only`, the one field to write: `headline`, `summary` or a role or project fact's id. Role and project facts are those whose ids start with `role-` and `project-`. career-consultant writes it after loading its `write-job-portal-content` skill, with only `read_profile_facts` allowed. Each field lists the ids of the facts it rests on in `facts`. Three checks verify the answer:

- `coverage`: each field asked for is there, and each description is of a role or project.
- `citations`: each cited fact exists.
- `form`: each field keeps to its cap in `configurations.yaml` (headline 220 characters, summary 2600, description 2000), and is plain text, with bullets as `•`.

career-consultant's `document_prompt` adds the document to the system prompt only when the state has one, so the same agent writes job portal content with no document.

## Agent graphs

An agent graph is a LangGraph graph whose main node is an agent, with child agents joined as nodes beside it. It follows LangChain's [handoffs pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs) with agent subgraphs. career-director's is the only one: `src/agents/career_director/graph.py` builds it, and `/ezcareer/a2a/career-director` serves it.

- Each agent is a node named after it: the main agent `career-director`, and its children, today only `productivity-assistant`.
- The state keeps `active_agent`, the agent the conversation is with. A turn starts at that agent, and at career-director when there is none yet. The served graph keeps checkpoints per A2A context, so a follow-up about email goes straight to productivity-assistant and makes no director model call. This is the "active agent" routing that issue #86 asks for.
- career-director calls `handoff_to_child` with the child's name. Its choices are exactly the children joined to the graph.
- A child calls `handoff_to_parent` when a message isn't its to answer.
- A handoff tool returns `Command(goto=..., graph=Command.PARENT)`. It sets `active_agent` and passes on only the AI message that called it and a ToolMessage answering it, so the next agent sees a complete tool call and none of the last agent's own steps.
- An agent that answers without a tool call ends the turn.

Only an agent that joins the graph as a child gets `handoff_to_parent`:

- `build_agent` gives every agent `HandoffToParentMiddleware`. It registers the tool through `AgentMiddleware.tools`, and its `wrap_model_call` removes the tool from each model call with `request.override(tools=...)`, unless the run is a child node of an agent graph.
- The graph builder joins each child with `child.with_config(configurable={"parent_agent": ...})`. The tool hands back to that agent.
- So the same productivity-assistant instance that runs inside `triage-email` and `draft-reply`, or on its own, is never offered the tool.

Both handoff tools live in `src/tools/handoff.py`.

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

- Each tool of any agent that `system.md` or a skill names in backticks belongs to that agent.
- Each name under `include_tools` is one of the agent's skill tools.
- Each skill tool is listed by at least one skill, so the model can reach it.

## An agent works on its own

Called directly with its state in the A2A data part, an agent does its whole job. A workflow wraps it only to make a run deterministic: it loads the data, runs fixed steps and checks the result. It never supplies something the agent needs to work.

The direction is one way: a workflow runs an agent, and an agent never runs a workflow built on itself. productivity-assistant drafts a reply with its own reads, and `draft-reply` wraps it for Ops' Inbox.

So whatever an agent's model must see comes from the agent itself. career-consultant's `document_prompt` middleware, LangChain's `@dynamic_prompt`, adds `state["document"]` to the system prompt on every model call. The document reaches the model the same way whether a direct caller sent it or edit-document's `load` node loaded it.

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

`AllowedToolsMiddleware` applies the whitelist to always-on tools with LangChain's `wrap_model_call` and `request.override(tools=...)`. The resolver that `build_agent` gives `SkillsMiddleware` applies it to skill tools. The deepagents file tools that read skills are never whitelisted out.

## Tools ops-api executes

The harness has no database and no third-party credentials. When a node or tool needs something that Ops owns, it pauses the run and asks ops-api to execute a tool:

```python
interrupt({"execute_tool": "document", "id": document_id})
```

The A2A task becomes `input-required`, and its message carries the request as a data part. ops-api executes the tool for the run's user and resumes the task with the tool result, or with `{"error": ...}` when it can't. These tools exist today:

- `{"execute_tool": "document", "id": ...}`, from `write_document`'s `load` node.
- `{"execute_tool": "documents", "name": ..., "kind": ...}`, from career-director's `find_documents` tool.
- `{"execute_tool": "thread", "id": ...}`, from productivity-assistant's `read_thread` tool. ops-api returns `{"thread": ...}`, or `{"error": ...}` when it can't.
- `{"execute_tool": "free_slots", "days": ...}`, from productivity-assistant's `read_free_slots` tool. ops-api returns `{"free_slots": [...], "timezone": ...}`, with no slots when the user offers none.
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

- `{"execute_tool": "job_search", "query": ..., "location": ..., "country": ..., "remote_only": ..., "posted_within": ..., "employment_types": [...], "job_requirements": [...], "radius_km": ..., "max_jobs": ...}`, from job-analyst's `search_jobs` tool. The fields are the tool's arguments, with each field of the user's own search (`query`, `location`, `posted_within`) that is set and not empty over the agent's. The request names no job source: ops-api chooses one (today JSearch, on the user's own key) and returns `{"jobs": [...], "requests_left": ...}`. `jobs` are `JobPosting`s, newest first, each job once, and without jobs that break the user's work mode or country preferences. `requests_left` is how many requests the user's key has left, or `null` when the source didn't say. ops-api returns `{"error": ...}` when it can't search, for example when the user hasn't connected a job search key in Settings or the source is down. `search_jobs` gives the agent that error as a tool error, and the agent goes on with the jobs earlier searches found. find-jobs fails with the errors when no search succeeded, so career-director's `find_jobs` tells career-director why.
- `{"execute_tool": "job_run", "run_after": ..., "search": ...}`, from career-director's `schedule_job_run` tool. `run_after` is an ISO 8601 time with its offset, or `null` to run as soon as a worker is free; `search` is a `JobSearch` (`query`, `location`, `posted_within`), or `null` to search from the user's preferences. ops-api queues a run of its job agent and returns `{"id": ..., "run_after": ...}`, or `{"error": ...}` when it can't, for example when an agent run is already queued. No approval is needed: the run only adds jobs for the user to look at.

A question for the user, from `clarify`, pauses the run in the same way, with a widget instead of `execute_tool`.

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

Metadata carries no credentials, and `RunMetadata` refuses any other field. The harness holds no third-party key apart from its own model keys: a tool that needs the user's account, such as Gmail or a job search, asks ops-api to execute a [tool](#tools-ops-api-executes), and ops-api makes the call.

## Streaming

Clients call `SendStreamingMessage`. `LanggraphExecutor` streams the graph with `stream_mode=["values", "messages", "tasks"]` and turns it into A2A events:

- **Steps.** Each node, tool call and subgraph task is a working status update whose data part is `{"step": ...}`.
- **Agent graphs.** In career-director's graph, `Executable.agent_nodes` names the nodes that run an agent. The executor drops that node from each step's and model chunk's namespace, so whichever agent runs streams its tool calls, thinking and text as if it were served alone. A handoff ends its agent with `Command.PARENT`, so its tool task never reports a result. The step closes when the agent's node ends, with the next agent's name as its detail.
- **Step details.** A finished step carries `detail`, a short result or target in plain words, such as `1 cover letter`. A tool sets it by returning `{"step_detail": ...}` in its ToolMessage artifact, beside `name` and `data` when it also publishes one. A tool call's step reads its own tool's detail. A node's step reads the last detail its tools set. `find_documents` sets the count by kind, `edit_document` the document's title, and `propose_changeset` the first fact its edits cite, such as `citing Acme Payments`.
- **Usage.** Each model call that ends, in any agent, workflow node or tool's workflow, is a working status update whose data part is `{"usage": ...}`. A LangChain callback handler, `UsageReporter`, reads the call's final `AIMessage`. The part carries `provider` (the model's family in `[models]`), `model` (as `[models]` names it), `agent` (the nearest configured agent graph the call runs in, else the executable), `node`, LangChain's `input_tokens` and `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`, `latency_ms`, `stop_reason` and `request_id`. Tokens are 0 when the provider sent no usage, and a call that fails sends nothing. glm models set `stream_usage` so the gateway streams usage. A blocking `SendMessage` returns these messages in the task's `history`.
- **Thinking and text.** The model's reasoning and text stream as `thinking` and `text` artifacts, one per model turn. For a workflow, they come from the node that `Executable.reply_node` names.
- **Tool artifacts.** A tool that returns an artifact `{"name": ..., "data": ...}` publishes it as an artifact of that name. `propose_changeset` publishes `changeset` this way.
- **Reply.** The final answer is an artifact named after the executable. Then the task completes, fails, or asks for input.
- **Failure.** A failed task's status message carries the reason as text. When the user must add something before the run can work, it also carries a data part `{"next": {"label": ..., "screen": ...}}`, where `screen` is `portfolio`, `documents`, `jobs` or `settings`. Raise `ExecuteError(reason, NextStep(...))` to set it. `require_facts` fails analyse-job and find-jobs this way when the profile has no facts.

`CancelTask` stops a run.
