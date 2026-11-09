---
name: modify-career-documents
description: How to write a Changeset of edits to a résumé or cover letter, with paths, sources and the rules each edit kind follows.
---

# Modify a career document

1. Read the request and the document JSON. Find the smallest set of edits that does what the user asked. Don't change anything else.
2. Read the PDF lines and the profile facts you need with `read_pdf_lines` and `read_profile_facts`.
3. Write each edit. A path is the ids from the content root, joined with `/`, such as `blocks/experience/items/lumen/bullets/queue/text`.
   - `update_field` replaces one field. Its value has the field's type. `null` clears an optional field.
   - `insert_block` adds a block after the block named by `after`, or first when `after` is `null`.
   - `insert_item` adds a list item, such as a bullet or a skill, after the item named by `after`.
   - `move` moves a block or an item within its list.
   - `delete` removes a block or an item. A block that a layout places can only go after the layout drops it.
   - `update_visibility` hides or shows a block without deleting it.
   - `update_design` sets the whole design. Copy the current design and change only what the user asked.
4. Cite sources in every value's `src`. Rewording a line cites that line. A claim the PDF doesn't make cites the fact that supports it. Keep every number and name exactly as the cited line or fact has it.
5. New ids are short, lowercase and unique among their siblings, such as `k8s-bullet`.
6. Write `reason` as one sentence the user reads, saying what the changeset does and why.
