---
name: analyse-job
description: Map every requirement in a job posting to the user's profile facts as met, partly met or not met, citing posting lines and facts.
---

# Analyse a job posting

1. Read the whole posting. Find every skill, qualification, experience or duty the posting asks the candidate to have. Skip the company blurb, benefits and the application process.
2. For each requirement, copy its text word for word from the posting. Copy a span, don't paraphrase or merge two requirements. One bullet that asks for two things is two requirements, each with its own span.
3. Set `line_ids` to the numbers of the lines the text comes from, in order. Most requirements sit on one line.
4. Set `importance`:
   - `nice_to_have` when the posting says preferred, a plus, bonus, nice to have, ideally or similar, or lists it under such a heading.
   - `required` otherwise.
5. Call `read_profile_facts` once and match each requirement against the facts:
   - `met` when facts show all of it.
   - `partly` when facts show some of it, such as a related tool, fewer years, or the same work at a smaller scale.
   - `not_met` when no fact shows it.
6. Set `fact_ids` to every fact that supports the match, as `fact:<id>`. `met` and `partly` need at least one. `not_met` can cite a fact that shows the closest thing the user has.
7. Write `reason` as one plain sentence naming what the facts show or what is missing.

A check verifies your answer. Each cited line and fact must exist, and each requirement's text must appear word for word in its cited lines. When it reports errors, fix only the requirements it names.
