# ezcareer-harness architecture

ezcareer-harness serves career agents and workflows over A2A. Ops (ops-api and ops-web) is its only client. Read this page before you change how the harness is put together: its layers, agents, workflows, tools, skills or the A2A contract. Follow [the coding guidelines](../development/coding-guidelines.md) for the code itself.

## Layers

| Folder               | Holds                                                                                                                                                                                                                 |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/app`            | The A2A server, the dependency-injector containers, and `Executable`, which serves a graph at `/ezcareer/a2a/<name>`                                                                                                  |
| `src/core`           | Settings (`config.toml`, environment) and errors                                                                                                                                                                      |
| `src/agents`         | One folder per agent: `profile.yaml`, `system.md`, `skills/`, `state.py`, and the agent's own `tools/` and `checks/`. Also `build_agent`, `AgentOverride`, the shared middlewares and career-director's handoff graph |
| `src/features`       | One folder per workflow: `graph.py`, `nodes/`, `checks/`, `schemas.py` and `harness/configurations.yaml`                                                                                                              |
| `src/tools`          | Tools that more than one agent uses, such as `read_profile_facts`, `clarify`, `permission` and the handoff tools                                                                                                      |
| `src/adapters`       | Adapters for outside data sources, such as the job sources behind `search_jobs`                                                                                                                                       |
| `src/clients`        | Clients of other services, and the LLM providers                                                                                                                                                                      |
| `src/shared`         | Types and helpers that several layers use, such as the profile, job postings and checks                                                                                                                               |
| `src/infrastructure` | Observability and persistence                                                                                                                                                                                         |

Import rules:

- `adapters`, `agents`, `clients`, `shared` and `tools` never import `features`.
- A feature never imports another feature. The one exception is `find_jobs`, which runs `analyse_job` through its package barrel.

`tests/test_architecture.py` enforces both rules.

## Agents and workflows

| Agent             | Workflows it runs                                | Served as an agent             |
| ----------------- | ------------------------------------------------ | ------------------------------ |
| job-finder        | `analyse-job`, `find-jobs`                       | yes                            |
| career-consultant | `edit-document` (`src/features/write_document`)  | yes                            |
| career-director   | none; it runs the others as its tools            | yes                            |
| email-assistant   | `triage-email`, `draft-reply`                    | inside career-director's graph |
| resume-importer   | `import-resume` (`src/features/import_document`) | no                             |

email-assistant reads the emails of the user's job search and drafts the user's replies. It never sends anything. career-director hands it the conversation when the user asks about their email (see [Handoffs](#handoffs)). It finds threads with its `search_threads` tool and drafts with its `draft_reply` tool.

`search_threads` filters by the days a message was sent (`since`, `until`), a keyword, a sender and whether a thread has an attachment. It shows the agent at most `max_threads` threads (20, under `[email]` in `config.toml`), inside `<threads untrusted>` like a thread the agent reads. When more match, its result ends with how many were left out and tells the agent to ask the user to narrow the search.

`draft_reply` fetches the thread and the user's free slots, then runs `draft-reply`. That workflow answers a thread, or writes a follow-up for an application when there is no thread, and offers free slots by id so code returns only slots the user has free. Its `configurations.yaml` keeps a long thread or calendar from filling the context:

- `max_free_slots` (12) shows the agent only the earliest slots.
- `max_thread_messages` (6) shows only the latest messages of the thread, and says how many earlier ones are left out.
- `max_message_chars` (4000) cuts each message to that length and marks it `[cut]`.

draft-reply runs on email-assistant, the agent that owns the `draft_reply` tool. So the container hands the tool the workflow through `providers.Self`, which breaks the cycle between the agent and its workflow.

`triage-email` uses its model only to read a thread. Code matches the thread to an application by the company it names, narrowed by role, and keeps `decide_by` only for an offer and `interview` only for a confirmed interview.

resume-importer only structures the file's lines. `import-resume` picks the draft's look in code: its `extract` node measures the file's layout (`layout.py`: columns, rules, tinted strips, a coloured band, a photo, the body font and the name's colour) and suggests the closest document-renderer template. The draft is made in that template, and the result's `suggestion` names it with the columns and traits it rests on.

## Handoffs

career-director is served as a LangGraph graph of agents, following LangChain's [handoffs pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs) with agent subgraphs. `src/agents/career_director/graph.py` builds it:

- Each agent is a node named after it: `career-director` and its children, today only `email-assistant`.
- The state keeps `active_agent`, the agent the conversation is with. A turn starts at that agent, and at career-director when there is none yet. The served graph keeps checkpoints per A2A context, so a follow-up about email goes straight to email-assistant and makes no director model call. This is the "active agent" routing that issue #86 asks for.
- career-director calls `handoff_to_child` with the child's name. email-assistant calls `handoff_to_parent` when a message isn't about email.
- A handoff tool returns `Command(goto=..., graph=Command.PARENT)`. It sets `active_agent` and passes on only the AI message that called it and a ToolMessage answering it, so the next agent sees a complete tool call and none of the last agent's own steps.
- An agent that answers without a tool call ends the turn.

Both handoff tools live in `src/tools/handoff.py`. The child's agent is the same instance the email workflows run, and those workflows' `AgentOverride` whitelists leave the handoff and email tools out.

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

`tests/app/test_agent_tools.py` checks every served agent:

- Each tool that `system.md` or a skill names in backticks belongs to that agent.
- Each name under `include_tools` is one of the agent's skill tools.
- Each skill tool is listed by at least one skill, so the model can reach it.

## An agent works on its own

Called directly with its state in the A2A data part, an agent does its whole job. A workflow wraps it only to make a run deterministic: it fetches the data, runs fixed steps and checks the result. It never supplies something the agent needs to work.

So whatever an agent's model must see comes from the agent itself. career-consultant's `document_prompt` middleware, LangChain's `@dynamic_prompt`, adds `state["document"]` to the system prompt on every model call. The document reaches the model the same way whether a direct caller sent it or edit-document's `load` node fetched it.

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

## Data requests

The harness has no database. When a node or tool needs data that Ops owns, it pauses the run with a data request:

```python
interrupt({"fetch": "document", "id": document_id})
```

The A2A task becomes `input-required`, and its message carries the request as a data part. ops-api answers with the data and resumes the task. These requests exist today:

- `{"fetch": "document", "id": ...}`, from `write_document`'s `load` node.
- `{"fetch": "documents", "name": ..., "kind": ...}`, from career-director's `find_documents` tool.
- `{"fetch": "thread", "id": ...}`, from email-assistant's `draft_reply` tool. ops-api answers `{"thread": ...}`, or `{"error": ...}` when it can't.
- `{"fetch": "free_slots", "days": ...}`, from `draft_reply` next. ops-api answers `{"free_slots": [...], "timezone": ...}`, with no slots when the user offers none.
- `{"fetch": "threads", "since": ..., "until": ..., "keyword": ..., "sender": ..., "has_attachment": ..., "limit": ...}`, from email-assistant's `search_threads` tool. Each filter is `null` when the agent didn't set it. `since` and `until` are ISO dates and include their day. `sender` matches a name, an address or a domain. `limit` is the most threads to send.

  ops-api answers with the matching threads, latest first and at most `limit`, and how many match in all:

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

  `sender` and `last_sent_at` are the latest message's. It answers `{"error": ...}` when it can't search, for example when the user's inbox isn't connected.

A question for the user, from `clarify` or `permission`, pauses the run in the same way, with a widget instead of `fetch`.

## Run metadata

A request's `params.metadata` sets up one run. `LanggraphExecutor` validates it as `RunMetadata` and hands it to the graph as the `RunContext` runtime context:

- `model` picks the model every LLM call of the run uses. `dynamic_model_call` applies it. Without it, each agent keeps its own.
- `jsearch.api_key` is the user's own RapidAPI key. `search_jobs` hands the run context to each job source, and JSearch searches on this key instead of `EZCAREER_HARNESS_JSEARCH__API_KEY`.

A key in metadata stays out of the message, the task store and the logs. It is a `SecretStr`, `RunMetadata` hides its input in validation errors, and the logging setup drops the A2A server's debug line that dumps the request body.

## Streaming

Clients call `SendStreamingMessage`. `LanggraphExecutor` streams the graph with `stream_mode=["values", "messages", "tasks"]` and turns it into A2A events:

- **Steps.** Each node, tool call and subgraph task is a working status update whose data part is `{"step": ...}`.
- **Handoffs.** In career-director's graph, `Executable.agent_nodes` names the nodes that run an agent. The executor drops that node from each step's and model chunk's namespace, so whichever agent runs streams its tool calls, thinking and text as if it were served alone. A handoff ends its agent with `Command.PARENT`, so its tool task never reports a result. The step closes when the agent's node ends, with the next agent's name as its detail.
- **Step details.** A finished step carries `detail`, a short result or target in plain words, such as `1 cover letter`. A tool sets it by returning `{"step_detail": ...}` in its ToolMessage artifact, beside `name` and `data` when it also publishes one. A tool call's step reads its own tool's detail. A node's step reads the last detail its tools set. `find_documents` sets the count by kind, `edit_document` the document's title, and `propose_changeset` the first fact its edits cite, such as `citing Acme Payments`.
- **Thinking and text.** The model's reasoning and text stream as `thinking` and `text` artifacts, one per model turn. For a workflow, they come from the node that `Executable.reply_node` names.
- **Tool artifacts.** A tool that returns an artifact `{"name": ..., "data": ...}` publishes it as an artifact of that name. `propose_changeset` publishes `changeset` this way.
- **Reply.** The final answer is an artifact named after the executable. Then the task completes, fails, or asks for input.
- **Failure.** A failed task's status message carries the reason as text. When the user must add something before the run can work, it also carries a data part `{"next": {"label": ..., "screen": ...}}`, where `screen` is `portfolio`, `documents`, `jobs` or `settings`. Raise `ExecuteError(reason, NextStep(...))` to set it. `require_facts` fails analyse-job and find-jobs this way when the profile has no facts, and JSearch fails a search this way when neither the run nor the server has a key.

`CancelTask` stops a run.
