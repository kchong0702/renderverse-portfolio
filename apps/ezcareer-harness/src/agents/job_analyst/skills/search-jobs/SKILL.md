---
name: search-jobs
description: Turn the user's profile and preferences into a few search_jobs queries that find fresh jobs worth ranking.
metadata:
  include_tools: search_jobs
---

# Search for jobs

1. Call `read_profile_facts` once. Note the user's most recent job titles and their strongest skills.
2. Write the query as a job title the user has held or is ready for, such as "senior backend engineer", with at most one of their strongest skills. Each extra word narrows the search, so a title with several skills often finds nothing.
3. Pass the preferences as arguments, not as query words:
   - `location` only when the user names a city or region.
   - `country` as one of the preferred countries. With several, run the query once for each. Leave it out only when none is set: a search without it is not worldwide.
   - `remote_only` when the user accepts only remote work.
   - `posted_within` stays `week` unless the user asks for older jobs.
   - `employment_types`, `job_requirements` and `radius_km` only when the user asks for them.
4. Run the queries. Each `search_jobs` result already has no duplicates and is sorted newest first, so don't do either yourself.
5. When a query returns fewer than five relevant jobs, run a broader one: drop the skill, or shorten the title. Never more than three queries in all, counting each country's. Never invent a job or a job id.
6. When a search fails, its result says why. Run it again only after changing it, and rank the jobs the other searches found.
