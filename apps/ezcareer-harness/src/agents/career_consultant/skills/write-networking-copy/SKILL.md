---
name: write-networking-copy
description: How to write the user's headline, summary and role and project descriptions for job portals and networking sites, aimed at the jobs they want, with every field citing the facts it rests on.
---

# Write networking copy

1. Call `read_profile_facts` once. Every fact counts here, including facts the user switched off for the assistant.
2. Write only the fields the request asks for, within the caps it gives:
   - `headline` is one line: who the user is and what they offer the jobs they aim for, such as `Backend engineer | Payments and billing platforms | Go, Kubernetes`.
   - `summary` is the about section: two to four short paragraphs, one per line, in the first person. Open with what the user does and the jobs they aim for, then their strongest results.
   - `descriptions` has one description per role or project fact the request names, with that fact's id in `fact`. Open with one line on the scope, then the results as bullets, each line starting with `• `.
3. Aim the wording at the target roles: lead with the facts that matter most to them and use the terms those jobs use, where a fact shows the user has the skill.
4. Never claim anything no fact shows. Keep every number, name, employer and job title exactly as the facts have them. Never present a target role as a job the user has held.
5. List the facts each field rests on in its `facts`, by id without `fact:`, such as `role-1` for `fact:role-1`. A field that names a number, a tool or an employer cites the fact that has it.
6. Write plain text only. No Markdown or HTML: no `#`, `*`, `-` or numbered lists, bold or links. Bullets are `•`.

## Checks

A check verifies your answer. Each field asked for must be there. Each cited fact must exist. Each field must keep to its cap and be plain text. When it reports errors, fix only what it names.
