---
name: modify-career-documents
description: How to write a Changeset of edits to a résumé or cover letter, with paths, sources and the rules each edit kind follows.
metadata:
  include_tools: read_pdf_lines propose_changeset list_design_options
---

# Modify a career document

1. Read the request and the document JSON. Find the smallest set of edits that does what the user asked. Don't change anything else.
2. Read the PDF lines and the profile facts you need with `read_pdf_lines` and `read_profile_facts`.
3. Write each edit. A path is the ids from the content root, joined with `/`, such as `blocks/experience/items/lumen/bullets/queue/text`.
   - `update_field` replaces one field. Its value has the field's type. `null` clears an optional field.
   - `insert_block` adds a block after the block named by `after`, or first when `after` is `null`.
   - `insert_item` adds an item to the list that `parent` names, after the item named by `after`, or first when `after` is `null`. The item has the fields of that list's other items, such as `{id, text}` for a bullet or `{id, label, items}` for a skill row.
   - `move` moves a block or an item within its list, after the one named by `after`, or first when `after` is `null`.
   - `delete` removes a block or an item. A block that the design's `layouts` places can be deleted only in a changeset whose `update_design` also takes it out of every placement.
   - `update_visibility` hides or shows a block without deleting it.
   - `update_design` sets the whole design. Call `list_design_options` first for the templates this document's kind can use, with each one's fonts and accent colour. Copy the current design and change only what the user asked.
4. Cite sources in every value's `src`, as PDF line ids or `fact:<id>`. Rewording a line cites that line. A claim the PDF doesn't make cites the fact that supports it. The check rejects a value that cites nothing or an id that doesn't exist. Keep every number and name exactly as the sources have them, and never add one they don't.
5. New ids are short, lowercase and unique among their siblings, such as `k8s-bullet`.
6. Set the changeset's `id` to a new short id and `agent` to `career-consultant`. Write `reason` as one sentence the user reads, saying what the changeset does and why.
7. Propose the changeset with `propose_changeset`.
