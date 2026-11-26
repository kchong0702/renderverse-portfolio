---
name: tailor-to-job
description: How to tailor the document to a job on the user's Jobs page, by the job's id, on a copy made for that job.
metadata:
  include_tools: copy_for_job
---

# Tailor a document to a job

1. Call `copy_for_job` with the job's id before any edit. When `read_document` gives a `job_id`, the document you were given already belongs to that job, so use that id. It returns the job's posting and the document to work on from then on: the job's résumé, CV or cover letter of the same kind, copied now from the document you were given when the job has none yet, or the document itself when it is already the job's. Edit only the document it returns.
   - When the job already has a copy, keep editing it. Set `start_over` only when the user asks to start the copy over. It keeps the copy's current draft as a version the user can restore, then replaces the draft with the document you were given. When the document you were given is the job's copy, it replaces the draft with the document the copy was made from, or with that document's own source when it was itself a job's copy. That may not be a master. Starting over rejects any proposal on the copy still waiting for the user, and the answer says so.
2. Load the `resume-ats-optimizer` skill and tailor the copy to the posting's requirements, closing the gaps the profile supports.
3. Propose the edits to the copy with `propose_changeset`, as the `modify-career-documents` skill describes.
