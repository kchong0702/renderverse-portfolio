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

type StoredDocument = AnyDocument & { design: Required<Design> };

export interface DocumentRecord extends DocumentSummary {
  body: StoredDocument;
  lines: { id: string; text: string }[];
  pending_body: StoredDocument | null;
}

export interface Changeset {
  id: string;
  agent: string;
  edits: Edit[];
  reason: string;
  status: "pending" | "accepted" | "rejected";
}

export interface ChangesetRecord {
  id: string;
  changeset: Changeset;
  created_at: string;
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

export const deleteDocument = (id: string) => http.delete(`${URL}/${id}`);

export const setMaster = (id: string) =>
  http.put<DocumentRecord>(`${URL}/${id}/master`, {});

export const fetchRender = (id: string) =>
  http.get<Render>(`${URL}/${id}/render`);

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

export const undoChangesetEdit = ({
  id,
  changesetId,
  index,
}: {
  id: string;
  changesetId: string;
  index: number;
}) => http.delete(`${URL}/${id}/changesets/${changesetId}/edits/${index}`);

export const fetchImports = (signal?: AbortSignal) =>
  http.get<DocumentImport[]>(`${URL}/imports`, signal);

export const startImport = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return http.post<DocumentImport>(`${URL}/imports`, form);
};

export const cancelImport = (id: string) => http.delete(`${URL}/imports/${id}`);

export const readImport = (id: string) =>
  http.post<DocumentImport>(`${URL}/imports/${id}/read`);
