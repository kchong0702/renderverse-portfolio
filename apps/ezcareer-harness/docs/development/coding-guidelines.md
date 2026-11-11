# Coding guidelines

These rules apply to all code in ezcareer-harness. For how the harness is put together, read [the architecture overview](../architecture/overview.md).

## Follow the library's convention

Before you build a mechanism, check whether LangChain, LangGraph, deepagents or another library the harness uses already has one. If it does, use it the way its documentation shows. Don't invent a parallel version.

Examples in this codebase:

| Need                                       | Convention used                                                                                                                   |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| Offer a tool only after a skill is read    | deepagents `metadata.include_tools` with `SkillsMiddleware(tools=...)`                                                            |
| Change the tools or the model for one call | LangChain `wrap_model_call` with `request.override(...)`                                                                          |
| Pause a run for input                      | LangGraph `interrupt` and `Command(resume=...)`                                                                                   |
| Hand the conversation to another agent     | LangChain handoffs: agents as graph nodes, a tool returning `Command(goto=..., graph=Command.PARENT)` and `active_agent` in state |
| Offer a tool only in some runs             | A LangChain middleware that registers it in `AgentMiddleware.tools` and filters it in `wrap_model_call`                           |
| Stream a run                               | LangGraph `astream` with `stream_mode` and `subgraphs=True`                                                                       |
| Retry and stop calling a failing service   | `tenacity` and `circuitbreaker`                                                                                                   |
| Wire singletons and dependencies           | `dependency-injector` containers                                                                                                  |

If the library's convention doesn't fit, say why in the PR description before you write your own.

## Agents, workflows and agent graphs

Read [the architecture overview](../architecture/overview.md) for the three kinds of graph. When you write one:

- An agent never runs a workflow built on itself. Give it tools that do the work, and wrap it in a workflow only to make a run deterministic.
- To add a child to an agent graph, join its agent in the graph builder and add its name to the main agent's `handoff_to_child` choices. Don't add `handoff_to_parent` to its tools: `HandoffToParentMiddleware` offers it only inside the graph.
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
- A service calls another feature's service, not its repository.

## Types

- Use the real type. Don't use `Any` or a bare `dict`.
- Put model config inside each class. Don't add a base class only to share config.
- Prefer being explicit over silencing a linter or type checker.

## Names

- A name says exactly what the thing is or does. Rename a misleading name.

## Docstrings and comments

- Don't put a docstring on a class itself.
- Give every function, and every field in a class, a docstring of at most two lines. Say what it does, not what happens around it.
- A tool's schema carries its description, and the model sees each description once.
- Don't write code comments. Log with structlog, not `print`.

## Git

- Use Conventional Commits: `type(scope): summary`, with `feat`, `fix`, `refactor` or `chore`, and `ezcareer-harness` as the scope.
- Rebase onto the base branch. Never merge it in. Force-push only after a rebase, with `--force-with-lease`.
- Show evidence in the PR that the change works, and keep the PR small enough to review.
