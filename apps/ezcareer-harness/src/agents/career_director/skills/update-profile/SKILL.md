---
name: update-profile
description: Change the user's Data, their profile's about fields, links, roles, education, projects and skills, from one of their documents or from what they ask, saved only once they approve.
metadata:
  include_tools: preview_profile_sync update_profile
---

# Update the profile

Nothing is saved until the user approves your `update_profile` call on a card in the chat.

1. To sync the profile with a résumé or CV, first find it with `find_documents`, as the system prompt says. Then call `preview_profile_sync` with its id. The preview lists the edits the document brings.
2. Keep only the edits the user asked for. When they asked for everything, keep them all. When the preview has none, tell the user the profile already matches and stop.
3. For a change the user asks for directly, write the edit yourself from the field they named. "Change my headline to X" is `{"kind": "about", "field": "headline", "value": "X"}`. Don't read anything first. Leave out a `new_skill` the user already has: a name matching one of their skills, ignoring case and archived ones included, is refused with the reason, which you tell the user.
4. To change a role, education or project, call `read_profile_facts` for its fact id, the part after `fact:`, such as `role-<uuid>`. Never guess or make up an id.
5. Call `update_profile` once, with every edit in one call. Set `source` to the document's title when the edits come from a document, and leave it empty otherwise. Never call `update_profile` twice in one turn.
6. When the user rejects the call, don't try again unless they ask. When they gave a reason, follow it.
7. Reply in one sentence: what was saved, or that nothing changed.
