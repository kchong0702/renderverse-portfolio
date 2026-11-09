import { http } from "@/shared/api/http";

export type DocumentKind = "resume" | "cv" | "cover_letter";
export type Font =
  | "inter"
  | "lato"
  | "source-sans-3"
  | "source-serif-4"
  | "merriweather"
  | "eb-garamond";
export type Size = "small" | "medium" | "large";
export type PageSize = "a4" | "letter";
export type Alignment = "left" | "justify";
export type ChangesetStatus = "pending" | "accepted" | "rejected";
export type ImportStatus = "pending" | "done" | "failed";

export type Json =
  string | number | boolean | null | Json[] | { [key: string]: Json };

export interface Value {
  text: string;
  src: string[];
}

export interface RichValue {
  html: string;
  align?: string | null;
  src: string[];
}

export interface Block {
  id: string;
  kind: string;
  hidden?: boolean;
  [field: string]: Json | undefined;
}

export interface Design {
  template: string;
  accent: string | null;
  font: Font | null;
  text_size: Size;
  line_spacing: number;
  alignment: Alignment;
  margins_mm: number;
  section_spacing_pt: number;
  page_size: PageSize;
  photo_shape: "circle" | "rounded" | "square";
  photo_size: Size;
  layouts: Record<string, Record<string, string[]>>;
}

export interface DocumentBody {
  format?: "document/v1";
  kind: DocumentKind;
  language?: string;
  design?: Design;
  assets?: Record<string, { media_type: string; uri: string }>;
  content: { blocks: Block[] };
}

export type Edit =
  | { kind: "update_field"; path: string; value: Json }
  | { kind: "insert_block"; after: string | null; block: Block }
  | { kind: "insert_item"; parent: string; after: string | null; item: Json }
  | { kind: "move"; path: string; after: string | null }
  | { kind: "delete"; path: string }
  | { kind: "update_visibility"; block: string; hidden: boolean }
  | { kind: "update_design"; design: Design };

export interface Changeset {
  id: string;
  agent: string;
  edits: Edit[];
  reason: string;
  status: ChangesetStatus;
}

export interface ChangesetRecord {
  id: string;
  changeset: Changeset;
  created_at: string;
}

export interface DocumentSummary {
  id: string;
  kind: DocumentKind;
  title: string;
  master: boolean;
  pending_edits: number;
  updated_at: string;
}

export interface DocumentRecord extends DocumentSummary {
  body: DocumentBody & { design: Design };
}

export interface Version {
  id: string;
  number: number;
  label: string;
  created_at: string;
}

export interface TemplateSpec {
  id: string;
  name: string;
  description: string;
  kinds: DocumentKind[];
  body_font: Font;
  heading_font: Font;
  accent: string;
}

export interface RenderWarning {
  kind: "split_entry" | "orphan_heading" | "region_overflow";
}

export interface Render {
  artifact: string;
  report: {
    pages: number;
    last_page_fill: number;
    warnings: RenderWarning[];
  };
}

export interface DocumentImport {
  id: string;
  filename: string;
  media_type: string;
  size: number;
  status: ImportStatus;
  document_id: string | null;
  error: string;
  created_at: string;
}

const URL = "/ops-api/v1/documents";

export const fetchDocuments = (signal?: AbortSignal) =>
  http.get<DocumentSummary[]>(URL, signal);

export const fetchDocument = (id: string, signal?: AbortSignal) =>
  http.get<DocumentRecord>(`${URL}/${id}`, signal);

export const createDocument = (create: { title: string; body: DocumentBody }) =>
  http.post<DocumentRecord>(URL, create);

export const renameDocument = ({ id, title }: { id: string; title: string }) =>
  http.patch<DocumentRecord>(`${URL}/${id}`, { title });

export const deleteDocument = (id: string) => http.delete(`${URL}/${id}`);

export const editDocument = ({ id, edits }: { id: string; edits: Edit[] }) =>
  http.post<DocumentRecord>(`${URL}/${id}/edits`, { edits });

export const setMaster = (id: string) =>
  http.put<DocumentRecord>(`${URL}/${id}/master`, {});

export const fetchRender = (id: string, signal?: AbortSignal) =>
  http.get<Render>(`${URL}/${id}/render`, signal);

export const fetchTemplates = (kind: DocumentKind, signal?: AbortSignal) =>
  http.get<TemplateSpec[]>(`${URL}/templates?kind=${kind}`, signal);

export const fetchVersions = (id: string, signal?: AbortSignal) =>
  http.get<Version[]>(`${URL}/${id}/versions`, signal);

export const keepVersion = ({ id, label }: { id: string; label: string }) =>
  http.post<Version>(`${URL}/${id}/versions`, { label });

export const restoreVersion = ({
  id,
  versionId,
}: {
  id: string;
  versionId: string;
}) => http.post<DocumentRecord>(`${URL}/${id}/versions/${versionId}/restore`);

export const fetchChangesets = (id: string, signal?: AbortSignal) =>
  http.get<ChangesetRecord[]>(`${URL}/${id}/changesets`, signal);

export const decideChangeset = ({
  id,
  changesetId,
  status,
}: {
  id: string;
  changesetId: string;
  status: "accepted" | "rejected";
}) =>
  http.put<ChangesetRecord>(`${URL}/${id}/changesets/${changesetId}`, {
    status,
  });

export const fetchImports = (signal?: AbortSignal) =>
  http.get<DocumentImport[]>(`${URL}/imports`, signal);

export const startImport = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return http.post<DocumentImport>(`${URL}/imports`, form);
};

export const cancelImport = (id: string) => http.delete(`${URL}/imports/${id}`);
