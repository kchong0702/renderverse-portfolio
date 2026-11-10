import type {
  AnyBlock,
  AnyDocument,
  Award,
  Bullet,
  Certification,
  Contact,
  ContactKind,
  CustomEntry,
  Date as DocumentDate,
  Degree,
  Design,
  Job,
  LanguageSkill,
  Link,
  Paragraph,
  Project,
  Publication,
  RichValue,
  Skill,
  Tag,
  Value,
} from "@renderverse/document-renderer";
import { http } from "@/shared/api/http";

export type DocumentKind = AnyDocument["kind"];
export type ImportStatus = "pending" | "running" | "done" | "failed";

export type Item =
  | Contact
  | Job
  | Degree
  | Project
  | Skill
  | LanguageSkill
  | Certification
  | Award
  | Publication
  | CustomEntry
  | Bullet
  | Link
  | Tag
  | Paragraph;

export type Edit =
  | {
      kind: "update_field";
      path: string;
      value: Value | RichValue | DocumentDate | ContactKind | Value[] | null;
    }
  | { kind: "insert_block"; after: string | null; block: AnyBlock }
  | { kind: "insert_item"; parent: string; after: string | null; item: Item }
  | { kind: "move"; path: string; after: string | null }
  | { kind: "delete"; path: string }
  | { kind: "update_visibility"; block: string; hidden: boolean }
  | { kind: "update_design"; design: Design };

export interface DocumentSummary {
  id: string;
  kind: DocumentKind;
  title: string;
  master: boolean;
  pending_changesets: number;
  updated_at: string;
}

export interface DocumentRecord extends DocumentSummary {
  body: AnyDocument & { design: Required<Design> };
}

export interface TemplateSpec {
  id: string;
  name: string;
  description: string;
  accent: string;
}

interface Render {
  artifact: string;
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

export const createDocument = (create: { title: string; body: AnyDocument }) =>
  http.post<DocumentRecord>(URL, create);

export const editDocument = ({ id, edits }: { id: string; edits: Edit[] }) =>
  http.post<DocumentRecord>(`${URL}/${id}/edits`, { edits });

export const setMaster = (id: string) =>
  http.put<DocumentRecord>(`${URL}/${id}/master`, {});

export const fetchRender = (id: string) =>
  http.get<Render>(`${URL}/${id}/render`);

export const fetchTemplates = (kind: DocumentKind, signal?: AbortSignal) =>
  http.get<TemplateSpec[]>(`${URL}/templates?kind=${kind}`, signal);

export const fetchImports = (signal?: AbortSignal) =>
  http.get<DocumentImport[]>(`${URL}/imports`, signal);

export const startImport = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return http.post<DocumentImport>(`${URL}/imports`, form);
};

export const cancelImport = (id: string) => http.delete(`${URL}/imports/${id}`);
