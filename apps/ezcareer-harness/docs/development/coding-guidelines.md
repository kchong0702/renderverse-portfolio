# Coding guidelines

These rules apply to all code in ezcareer-harness. For how the harness is put together, read [the architecture overview](../architecture/overview.md).

## Follow the library's convention

Before you build a mechanism, check whether LangChain, LangGraph, deepagents or another library the harness uses already has one. If it does, use it the way its documentation shows. Don't invent a parallel version.

Examples in this codebase:

| Need                                        | Convention used                                                                                                      |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Offer a tool only after a skill is read     | deepagents `metadata.include_tools` with `SkillsMiddleware(tools=...)`                                               |
| Change the tools or the model for one call  | LangChain `wrap_model_call` with `request.override(...)`                                                             |
| Pause a run for input                       | LangGraph `interrupt` and `Command(resume=...)`                                                                      |
| Give another agent a task                   | deepagents' sync subagent `task`: a tool that runs the subagent's agent inside the run and returns its final message |
| Offer a tool only in some runs              | A LangChain middleware that registers it in `AgentMiddleware.tools` and filters it in `wrap_model_call`              |
| Refuse a tool call before it runs           | LangChain `wrap_tool_call` returning an error `ToolMessage`, as `DuplicateTaskGuardMiddleware` does                  |
| Stream a run                                | LangGraph `astream` with `stream_mode` and `subgraphs=True`                                                          |
| Wire singletons and dependencies            | `dependency-injector` containers                                                                                     |
| Pass per-run data such as the model         | LangGraph runtime context (`RunContext`), read from `runtime.context`                                                |
| Keep a conversation across turns            | A LangGraph checkpoint thread per A2A context, as LangGraph's Agent Server does                                      |
| Summarise a long conversation               | deepagents' summarisation, which keeps its summary in the agent's state and retries a call that overflows            |
| Keep a side effect from rerunning on resume | A LangGraph `@task` inside the node or tool, which a nested graph runs again on resume                               |

If the library's convention doesn't fit, say why in the PR description before you write your own.

## Agents and workflows

Read [the architecture overview](../architecture/overview.md) for the two kinds of graph. When you write one:

- An agent never runs a workflow built on itself. Give it tools that do the work, and wrap it in a workflow only to make a run deterministic.
- To give an agent a subagent, add a tool to the agent that runs the subagent's agent, from its container, with the subagent profile's `recursion_limit`: the task's description as its only message, none of the caller's state, and only its final message back. This departs on purpose from deepagents' `task`, which passes the caller's state in and merges the subagent's changed keys back. Doing neither means parallel tasks can't clash on a shared key. Turn any error from the subagent's run, except LangGraph's `GraphBubbleUp`, into a `ToolException`, so a failed task fails only its own step. Build the subagent before the agent whose tool runs it.
- Build each agent once. Change what it is offered per run with config and middleware, not with a second instance.

## Simplicity

- Keep it simple. Add an abstraction, layer, base class or registry only when the task needs it now.
- Write something that is used in only one place inline. Don't extract it into a variable, function or type.
- Prefer a library over custom logic.
- Make the smallest change that does the task.
- Don't nest a function inside another function when a module-level function works.
- Remove folders, files and code that nothing uses anymore.

## Layout

- Name folders and files in snake_case. Hyphens appear only in app folders under `apps/` and in skill folders.
- Group related files into a folder, such as `nodes/`, `checks/` or `filters/`.
- Put a helper above the function that uses it. Put the file's main item at the bottom.
- Put data types in `types.py`, enums in `enums.py` and editable text in `values.py`, unless only one place uses them.
- Keep an exception that one package uses inside that package.
- Put tests under `tests/`, mirroring `src/`.
- Take settings such as URLs, limits and model names from config. Never hardcode them.
- Write `.env.example` with no comments and no commented-out variables. Leave each secret empty, and give every other variable the value that bootstraps the app locally.
- A service calls another feature's service, not its repository.

## Prompts

- Never hardcode a system prompt or a middleware's prompt in Python. Both go in prompt files. A tool's description and error messages, and a failure reason the user sees, stay in the code they belong to.
- Put an agent's system prompt in `src/agents/<agent>/prompts/system.md`. Add `prompts/system.<provider>.md` only when one provider needs different wording.
- Put each middleware's prompt in its own file, named after the middleware's module, and read it with `read_prompt`. Mark where run data goes with a `$name` placeholder and fill it with `string.Template`, so braces in the prompt stay literal. Read a prompt that a model call fills once per path, such as through a `functools.cache` function, not on every call.
- Start each prompt file with the front matter `read_prompt` validates: `version`, `description`, `author`, `date` and `status`. Quote `version`, such as `"1.10"`, because YAML reads an unquoted `1.10` as the number 1.1. Raise `version` and set `date` when you change the text.

## Types

- Use the real type. Don't use `Any` or a bare `dict`.
- Put model config inside each class. Don't add a base class only to share config.
- Prefer being explicit over silencing a linter or type checker.

## Names

- A name says exactly what the thing is or does. Rename a misleading name.
- A class-based middleware (an `AgentMiddleware` subclass) is named for what it provides, as a noun phrase ending in `Middleware`, such as `ToolAllowlistMiddleware` or `ResponseFormatMiddleware`. A function-based middleware (one made with a decorator such as `@wrap_model_call` or `@before_agent`) is named for what it does, starting with a verb, such as `dynamic_model_call`. Its module has the same name, in snake case.

## Docstrings and comments

- Don't put a docstring on a class itself.
- Give every function, and every field in a class, a docstring of at most two lines. Say what it does, not what happens around it.
- A tool's schema carries its description, and the model sees each description once.
- Don't write code comments. Log with structlog, not `print`.

## Migrations

- Generate every migration with `alembic revision --autogenerate`. Keep the file as Alembic writes it, its comments included.
- `env.py` and `script.py.mako` come from `alembic init -t async`. Leave `script.py.mako` as Alembic's template. Change `env.py` only where the app needs it, such as its database URL, engine, metadata and schema.
- When autogenerate misses something, fix the model so that it generates it. Don't edit the migration.
- If a migration needs a line autogenerate can't write, list each such line in the PR and say why.

## Git

- Use Conventional Commits: `type(scope): summary`, with `feat`, `fix`, `refactor` or `chore`, and `ezcareer-harness` as the scope.
- Rebase onto the base branch. Never merge it in. Force-push only after a rebase, with `--force-with-lease`.
- Show evidence in the PR that the change works, and keep the PR small enough to review.
