# ezcareer-harness architecture

ezcareer-harness serves career agents and workflows over A2A. Ops (ops-api and ops-web) is its only client. Read this page before you change how the harness is put together: its layers, agents, workflows, tools, skills or the A2A contract. Follow [the coding guidelines](../development/coding-guidelines.md) for the code itself.

## Layers

| Folder               | Holds                                                                                                                                                                                |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/app`            | The A2A server, the dependency-injector containers, and `Executable`, which serves a graph at `/ezcareer/a2a/<name>`                                                                 |
| `src/core`           | Settings (`config.toml`, environment) and errors                                                                                                                                     |
| `src/agents`         | One folder per agent: `profile.yaml`, `system.md`, `skills/`, `state.py`, and the agent's own `tools/` and `checks/`. Also `build_agent`, `AgentOverride` and the shared middlewares |
| `src/features`       | One folder per workflow: `graph.py`, `nodes/`, `checks/`, `schemas.py` and `harness/configurations.yaml`                                                                             |
| `src/tools`          | Tools that more than one agent uses, such as `read_profile_facts`, `clarify` and `permission`                                                                                        |
| `src/adapters`       | Adapters for outside data sources, such as the job sources behind `search_jobs`                                                                                                      |
| `src/clients`        | Clients of other services, and the LLM providers                                                                                                                                     |
| `src/shared`         | Types and helpers that several layers use, such as the profile, job postings and checks                                                                                              |
| `src/infrastructure` | Observability and persistence                                                                                                                                                        |

Import rules:

- `adapters`, `agents`, `clients`, `shared` and `tools` never import `features`.
- A feature never imports another feature. The one exception is `find_jobs`, which runs `analyse_job` through its package barrel.

`tests/test_architecture.py` enforces both rules.

## Agents and workflows

| Agent             | Workflows it runs                                | Served as an agent |
| ----------------- | ------------------------------------------------ | ------------------ |
| job-finder        | `analyse-job`, `find-jobs`                       | yes                |
| career-consultant | `edit-document` (`src/features/write_document`)  | yes                |
| career-director   | none; it runs the others as its tools            | yes                |
| email-assistant   | `triage-email`, `draft-reply`                    | no                 |
| resume-importer   | `import-resume` (`src/features/import_document`) | no                 |

email-assistant reads the emails of the user's job search and drafts the user's replies. It never sends anything. `draft-reply` answers a thread, or writes a follow-up for an application when there is no thread, and offers free slots by id so code returns only slots the user has free. career-director runs it as its `draft_reply` tool. `triage-email` uses its model only to read a thread. Code matches the thread to an application by the company it names, narrowed by role, and keeps `decide_by` only for an offer and `interview` only for a confirmed interview.

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
- `{"fetch": "thread", "id": ...}`, from career-director's `draft_reply` tool. ops-api answers `{"thread": ...}`, or `{"error": ...}` when it can't.
- `{"fetch": "free_slots", "days": ...}`, from `draft_reply` next. ops-api answers `{"free_slots": [...], "timezone": ...}`, with no slots when the user offers none.

A question for the user, from `clarify` or `permission`, pauses the run in the same way, with a widget instead of `fetch`.

## Run metadata

A request's `params.metadata` sets up one run. `LanggraphExecutor` validates it as `RunMetadata` and hands it to the graph as the `RunContext` runtime context:

- `model` picks the model every LLM call of the run uses. `dynamic_model_call` applies it. Without it, each agent keeps its own.
- `jsearch.api_key` is the user's own RapidAPI key. `search_jobs` hands the run context to each job source, and JSearch searches on this key instead of `EZCAREER_HARNESS_JSEARCH__API_KEY`.

A key in metadata stays out of the message, the task store and the logs. It is a `SecretStr`, `RunMetadata` hides its input in validation errors, and the logging setup drops the A2A server's debug line that dumps the request body.

## Streaming

Clients call `SendStreamingMessage`. `LanggraphExecutor` streams the graph with `stream_mode=["values", "messages", "tasks"]` and turns it into A2A events:

- **Steps.** Each node, tool call and subgraph task is a working status update whose data part is `{"step": ...}`.
- **Step details.** A finished step carries `detail`, a short result or target in plain words, such as `1 cover letter`. A tool sets it by returning `{"step_detail": ...}` in its ToolMessage artifact, beside `name` and `data` when it also publishes one. A tool call's step reads its own tool's detail. A node's step reads the last detail its tools set. `find_documents` sets the count by kind, `edit_document` the document's title, and `propose_changeset` the first fact its edits cite, such as `citing Acme Payments`.
- **Thinking and text.** The model's reasoning and text stream as `thinking` and `text` artifacts, one per model turn. For a workflow, they come from the node that `Executable.reply_node` names.
- **Tool artifacts.** A tool that returns an artifact `{"name": ..., "data": ...}` publishes it as an artifact of that name. `propose_changeset` publishes `changeset` this way.
- **Reply.** The final answer is an artifact named after the executable. Then the task completes, fails, or asks for input.
- **Failure.** A failed task's status message carries the reason as text. When the user must add something before the run can work, it also carries a data part `{"next": {"label": ..., "screen": ...}}`, where `screen` is `portfolio`, `documents`, `jobs` or `settings`. Raise `ExecuteError(reason, NextStep(...))` to set it. `require_facts` fails analyse-job and find-jobs this way when the profile has no facts, and JSearch fails a search this way when neither the run nor the server has a key.

`CancelTask` stops a run.
