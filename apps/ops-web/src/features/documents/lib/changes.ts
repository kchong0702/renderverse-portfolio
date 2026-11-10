import type { Edit } from "../api/documents";

type Texty = { text?: unknown; html?: unknown };

export const pathOf = (edit: Edit) =>
  edit.kind === "update_field"
    ? edit.path
    : edit.kind === "insert_item"
      ? `${edit.parent}/${edit.item.id}`
      : edit.kind === "insert_block"
        ? `blocks/${edit.block.id}`
        : null;

export const overlaps = (a: string, b: string) =>
  a === b || a.startsWith(`${b}/`) || b.startsWith(`${a}/`);

export const isPending = (paths: string[], path: string) =>
  paths.some((pending) => overlaps(pending, path));

const plain = (html: string) =>
  new DOMParser().parseFromString(html, "text/html").body.textContent ?? "";

export function firstText(
  node: unknown,
): { text: string; src: string[] } | null {
  if (typeof node !== "object" || node === null) return null;
  const { text, html } = node as Texty;
  const src = (node as { src?: string[] }).src ?? [];
  if (typeof text === "string") return { text, src };
  if (typeof html === "string") return { text: plain(html), src };
  for (const child of Object.values(node)) {
    const found = firstText(child);
    if (found) return found;
  }
  return null;
}

export const changedText = (edit: Edit) =>
  edit.kind === "update_field"
    ? firstText(edit.value)
    : edit.kind === "insert_item"
      ? firstText(edit.item)
      : edit.kind === "insert_block"
        ? firstText(edit.block)
        : null;
