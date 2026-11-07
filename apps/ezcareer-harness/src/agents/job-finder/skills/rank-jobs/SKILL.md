---
name: rank-jobs
description: Map each job's requirements to the user's profile facts and rank the jobs search_jobs returned, citing description lines and facts.
---

# Rank jobs

1. Drop jobs that break the user's preferences, such as an onsite job when the user wants remote only, or a country the user doesn't want.
2. For each remaining job, map its description the same way a single posting is analysed. Each requirement has:
   - `text` copied word for word from the description, one requirement per span.
   - `line_ids` with the numbers of the description lines it comes from.
   - `importance`. `nice_to_have` when the description says preferred, a plus, bonus or nice to have, and `required` otherwise.
   - `match` and `fact_ids`. `met` when facts show all of it, `partly` when they show some of it, and `not_met` when none do. `met` and `partly` cite at least one `fact:<id>`.
   - `reason`, one plain sentence.
3. Set `job_id` to the id exactly as `search_jobs` returned it. List each job once.
4. Put the best fits first. A job whose required items are met beats one that meets only nice-to-haves. Code orders the final list by the fit it computes and keeps your order for ties.

A check verifies your answer. Every job id must come from `search_jobs`, and every cited line and fact must exist in that job's description and the profile. Requirement text must be word for word. When it reports errors, fix only what it names.
