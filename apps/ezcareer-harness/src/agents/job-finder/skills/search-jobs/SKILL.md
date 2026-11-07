---
name: search-jobs
description: Turn the user's profile and preferences into a few search_jobs queries that find fresh jobs worth ranking.
---

# Search for jobs

1. Call `read_profile_facts` once. Note the user's most recent job titles and their strongest skills.
2. Write one to three queries. Each one is a job title the user has held or is ready for, plus one or two of their strongest skills. Add a city when the preferences name one.
3. Pass the preferences as arguments, not as query words:
   - `country` when the preferences name one country.
   - `remote_only` when the user accepts only remote work.
   - `date_posted` stays `week` unless the user asks for older jobs.
4. Run the queries. `search_jobs` already removes duplicates and sorts newest first, so don't do either yourself.
5. Stop searching once you have about ten jobs that look relevant. Never invent a job or a job id.
