import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

export type ImportSource = "documents" | "data";
export type ImportStatus =
  "queued" | "processing" | "done" | "failed" | "abandoned";

export type LookTrait =
  | "accent_band"
  | "photo"
  | "tinted_headings"
  | "ruled_headings"
  | "serif_font"
  | "coloured_name";

export interface ImportRecord {
  id: string;
  source: ImportSource;
  filename: string;
  media_type: string;
  size: number;
  status: ImportStatus;
  document_id: string | null;
  suggestion: {
    template: string;
    columns: 1 | 2;
    traits: LookTrait[];
  } | null;
  added: number;
  conflicts: number;
  matched: number;
  error: string;
  created_at: string;
  finished_at: string | null;
}

export const isActive = (row: ImportRecord) =>
  row.status === "queued" || row.status === "processing";

export const fetchActiveImports = (signal?: AbortSignal) =>
  http.get<ImportRecord[]>(`${config.opsApiUrl}/imports/active`, signal);
