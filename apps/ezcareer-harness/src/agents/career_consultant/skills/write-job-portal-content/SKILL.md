---
name: write-job-portal-content
description: How to write the user's headline, summary and role and project descriptions for their job portal and networking profiles, so recruiters searching for the roles they want find and shortlist them, with every field citing the facts it rests on.
---

# Write job portal content

This content makes the user's profile easy for recruiters to find and choose. It is not tailored to one job posting: the aim names the kind of roles the user wants to be found for.

1. Call `read_profile_facts` once. Every fact counts here, including facts the user switched off for the assistant.
2. Write only the fields the request asks for, within the caps it gives:
   - `headline` is the line recruiters see in search results. Lead with the role title recruiters search for, as the facts support it, then the user's specialism and two or three core skills, such as `Backend Engineer | Payments and billing platforms | Go, Kubernetes`.
   - `summary` is the about section: two to four short paragraphs, one per line, in the first person. Portals hide all but the first lines behind "see more", so those carry the pitch: what the user does, for which kind of role, and their strongest result. Use the main role title and core skills once or twice, naturally. End with the kind of role the user is open to.
   - `descriptions` has one description per role or project fact the request names, with that fact's id in `fact`. Open with one line on the scope, then the results as bullets, each line starting with `• `, leading with numbers where the facts have them.
3. Use the role titles and skill names recruiters search for, as the facts name them. Never stuff keywords, and never list a skill no fact shows.
4. Never claim anything no fact shows. Keep every number, name, employer and job title exactly as the facts have them. Never present a target role as a job the user has held.
5. List the facts each field rests on in its `facts`, by id without `fact:`, such as `role-1` for `fact:role-1`. A field that names a number, a tool or an employer cites the fact that has it.
6. Write plain text only. No Markdown or HTML: no `#`, `*`, `-` or numbered lists, bold or links. Bullets are `•`.

## Checks

A check verifies your answer. Each field asked for must be there. Each cited fact must exist. Each field must keep to its cap and be plain text. When it reports errors, fix only what it names.
