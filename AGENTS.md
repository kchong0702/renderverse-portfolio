<!-- nx configuration start-->
<!-- Leave the start & end comments to automatically receive updates. -->

# General Guidelines for working with Nx

- For navigating/exploring the workspace, invoke the `nx-workspace` skill first - it has patterns for querying projects, targets, and dependencies
- When running tasks (for example build, lint, test, e2e, etc.), always prefer running the task through `nx` (i.e. `nx run`, `nx run-many`, `nx affected`) instead of using the underlying tooling directly
- Prefix nx commands with the workspace's package manager (e.g., `pnpm nx build`, `npm exec nx test`) - avoids using globally installed CLI
- You have access to the Nx MCP server and its tools, use them to help the user
- For Nx plugin best practices, check `node_modules/@nx/<plugin>/PLUGIN.md`. Not all plugins have this file - proceed without it if unavailable.
- NEVER guess CLI flags - always check nx_docs or `--help` first when unsure

## Scaffolding & Generators

- For scaffolding tasks (creating apps, libs, project structure, setup), ALWAYS invoke the `nx-generate` skill FIRST before exploring or calling MCP tools

## When to use nx_docs

- USE for: advanced config options, unfamiliar flags, migration guides, plugin configuration, edge cases
- DON'T USE for: basic generator syntax (`nx g @nx/react:app`), standard commands, things you already know
- The `nx-generate` skill handles generator discovery internally - don't call nx_docs just to look up generator syntax


<!-- nx configuration end-->

# Coding Conventions

- Keep it simple, stupid: prefer the plainest code that does the job.
- If something is used in only one place, write it inline instead of extracting a separate variable or function.
- Aim for the smallest change that achieves the task.

# ezcareer-harness Architecture

- Before changing how `apps/ezcareer-harness` is put together (its layers, agents, workflows, tools, skills or A2A contract), read `apps/ezcareer-harness/docs/architecture/` and `apps/ezcareer-harness/docs/development/`, and update them in the same change.
- An agent owns all its tools and skills. A tool only one skill uses is a skill tool, listed under `metadata.include_tools` in that skill's `SKILL.md`.
- A workflow owns no tools and has no `tools/` folder. It may only whitelist its agent's tools by name with `AgentOverride(tools=...)`.
- Follow LangChain, LangGraph, deepagents or the relevant library's convention instead of inventing your own.

# Deslop and Review Large Changes

- A change is large when it alters architecture (adds, moves or removes services, layers, agents, tools, data stores, migrations or the A2A contract) or touches many files across apps.
- Before committing a large change or asking for review, run two passes on the whole diff:
  1. **Deslop.** Remove AI-generated slop without changing behaviour: comments, defensive checks on trusted paths, needless helpers, variables or casts, and anything inconsistent with the surrounding code. Use pstack's `deslop` skill when it is available.
  2. **Independent review.** A fresh agent that did not write the change reviews the diff for bugs, broken callers, stale docs and rule breaks. Use pstack's `thermo-nuclear-review` or `/code-review` when available. Fix every real finding, then run lint, typecheck and test again.
- Run both passes again after every later round of changes, not only after the first build.
- Say in the pull request which passes ran.

# Git Conventions

- Never add Claude, Anthropic, or any AI assistant as an author, co-author, or contributor: no `Co-Authored-By` trailers, and no AI attribution in commit messages, PR descriptions, issues, or review comments.
- Commit as the configured git user; never change `user.name` / `user.email`.
- Use Conventional Commits: `type(scope): summary`, with types `feat`, `fix`, `refactor`, `chore` and the Nx project (`renderverse`, `ezbot-harness`, `ops-web`, `ops-api`) or area (`i18n`, `lint`) as scope.
- Don't amend or rewrite existing commits just to change attribution unless explicitly asked.
- Never push to `main` or merge into it; changes reach `main` only through a pull request the user merges.
- Never `git merge main` into a branch; rebase it onto `main` instead.
- Never force push, except to update a branch after a rebase (use `--force-with-lease`).

# Pull Requests

- Make every pull request evidence-driven: show that the change works, not only what it changes. Include each kind of evidence that applies:
  - **Screenshots** of the real app for any UI change, before and after when the look changes. Attach them with `gh pr create --attach`.
  - **An architecture diagram** in Mermaid when the change adds or moves services, layers, agents, tools or data stores.
  - **A sequence diagram** in Mermaid when the change adds or alters a flow across services or agents, such as requests, handoffs, pauses or approvals.
- Under Testing, give what you ran and what it showed, such as commands and results, a real end-to-end run and its output, and anything not tested.
