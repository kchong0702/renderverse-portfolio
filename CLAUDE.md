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

# Git Conventions

- Never add Claude, Anthropic, or any AI assistant as an author, co-author, or contributor: no `Co-Authored-By` trailers, and no AI attribution in commit messages, PR descriptions, issues, or review comments.
- Commit as the configured git user; never change `user.name` / `user.email`.
- Use Conventional Commits: `type(scope): summary`, with types `feat`, `fix`, `refactor`, `chore` and the Nx project (`renderverse`, `ezbot-harness`, `ops-web`, `ops-api`) or area (`i18n`, `lint`) as scope.
- Don't amend or rewrite existing commits just to change attribution unless explicitly asked.
- Never push to `main` or merge into it; changes reach `main` only through a pull request the user merges.
- Never `git merge main` into a branch; rebase it onto `main` instead.
- Never force push, except to update a branch after a rebase (use `--force-with-lease`).
