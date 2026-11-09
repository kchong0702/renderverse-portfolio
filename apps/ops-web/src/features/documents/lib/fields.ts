import type { Block, Json, RichValue, Value } from "../api/documents";

export const BLOCK_KINDS = [
  "profile",
  "photo",
  "contacts",
  "summary",
  "experience",
  "education",
  "projects",
  "skills",
  "languages",
  "certifications",
  "awards",
  "publications",
  "custom",
  "recipient",
  "letter",
] as const;

export const FIELD_KEYS = [
  "address",
  "authors",
  "awarder",
  "bullets",
  "closing",
  "company",
  "date",
  "dates",
  "degree",
  "description",
  "doi",
  "fluency",
  "grade",
  "greeting",
  "heading",
  "headline",
  "issuer",
  "items",
  "label",
  "language",
  "links",
  "location",
  "name",
  "organization",
  "paragraphs",
  "role",
  "school",
  "subject",
  "subtitle",
  "tags",
  "text",
  "title",
  "url",
  "value",
  "venue",
] as const;

export type FieldKey = (typeof FIELD_KEYS)[number];

export type BlockKind = (typeof BLOCK_KINDS)[number];

export interface TextEntry {
  path: string;
  label: string;
  depth: number;
  value: Value | RichValue;
}

const SKIPPED = new Set([
  "id",
  "kind",
  "hidden",
  "src",
  "align",
  "start",
  "end",
]);

function isObject(node: Json): node is { [key: string]: Json } {
  return typeof node === "object" && node !== null && !Array.isArray(node);
}

function isText(node: { [key: string]: Json }): boolean {
  return (
    Array.isArray(node.src) &&
    (typeof node.text === "string" || typeof node.html === "string")
  );
}

function collect(
  node: Json,
  path: string,
  label: string,
  depth: number,
  out: TextEntry[],
) {
  if (Array.isArray(node)) {
    for (const item of node)
      if (isObject(item) && typeof item.id === "string")
        collect(item, `${path}/${item.id}`, label, depth + 1, out);
  } else if (isObject(node) && isText(node)) {
    out.push({
      path,
      label,
      depth,
      value: node as unknown as Value | RichValue,
    });
  } else if (isObject(node)) {
    const children = Object.entries(node).filter(([key]) => !SKIPPED.has(key));
    for (const [key, child] of [
      ...children.filter(([, child]) => !Array.isArray(child)),
      ...children.filter(([, child]) => Array.isArray(child)),
    ])
      collect(
        child,
        `${path}/${key}`,
        key === "text" ? label : key,
        depth,
        out,
      );
  }
}

export function textEntries(block: Block): TextEntry[] {
  const out: TextEntry[] = [];
  collect(
    block as { [key: string]: Json },
    `blocks/${block.id}`,
    "text",
    0,
    out,
  );
  return out;
}

export function plainText(value: Value | RichValue): string {
  return "html" in value ? value.html : value.text;
}

export function newText(value: Json): string {
  if (!isObject(value)) return typeof value === "string" ? value : "";
  if (typeof value.text === "string") return value.text;
  if (typeof value.html === "string") return value.html;
  return newText(value.text ?? null);
}

export function nodeAt(blocks: Block[], path: string): Json {
  let node: Json = { blocks } as { [key: string]: Json };
  for (const key of path.split("/")) {
    if (Array.isArray(node))
      node = node.find((item) => isObject(item) && item.id === key) ?? null;
    else if (isObject(node)) node = node[key] ?? null;
    else return null;
  }
  return node;
}

export function fieldKey(path: string): FieldKey | undefined {
  return path
    .split("/")
    .reverse()
    .map((part) => FIELD_KEYS.find((key) => key === part && key !== "text"))
    .find((key) => key !== undefined);
}

export function blockKind(kind: string): BlockKind | undefined {
  return BLOCK_KINDS.find((known) => known === kind);
}
