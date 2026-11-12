import i18n from "@/i18n";
import { ApiError, http } from "@/shared/api/http";
import { config } from "@/shared/config";
import type { EntryKind } from "@/features/portfolio";

export interface ProfileImport {
  id: string;
  filename: string;
  media_type: string;
  source: "data" | "documents";
  added: number;
  conflicts: number;
  matched: number;
  created_at: string;
}

export type ChangeField =
  | "name"
  | "headline"
  | "location"
  | "email"
  | "phone"
  | "summary"
  | "title"
  | "organisation"
  | "start"
  | "end"
  | "highlights"
  | "link"
  | "code_link"
  | "tools";

export type FieldValue = string | string[] | null;

export interface FieldChange {
  kind: "field";
  id: string;
  import_id: string;
  entry_id: string | null;
  field: ChangeField;
  current: FieldValue;
  conflict: FieldValue;
}

export interface ImportedEntry {
  kind: EntryKind;
  title: string;
  organisation: string;
  location: string;
  start: string | null;
  end: string | null;
  summary: string;
  highlights: string[];
  link: string | null;
  code_link: string | null;
  tools: string[];
}

export interface MatchChange {
  kind: "match";
  id: string;
  import_id: string;
  entry_id: string;
  entry: ImportedEntry;
}

export type Change = FieldChange | MatchChange;

export type ChangeChoice = "current" | "conflict" | "same" | "different";

export interface NetworkingText {
  text: string;
  facts: string[];
}

export interface Networking {
  aim: string;
  headline: NetworkingText | null;
  summary: NetworkingText | null;
  descriptions: (NetworkingText & { fact: string })[];
}

export interface NetworkingWrite {
  aim: string;
  only: string | null;
}

const URL = `${config.opsApiUrl}/profile`;

export const fetchImports = (signal?: AbortSignal) =>
  http.get<ProfileImport[]>(`${URL}/imports`, signal);

export const importFile = (file: File, onSent: () => void) =>
  new Promise<ProfileImport>((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    const request = new XMLHttpRequest();
    request.open("POST", `${URL}/imports`);
    request.setRequestHeader("Accept", "application/json");
    request.responseType = "json";
    request.upload.onload = onSent;
    request.onload = () =>
      request.status < 300
        ? resolve(request.response)
        : reject(
            new ApiError(
              request.status,
              typeof request.response?.detail === "string"
                ? request.response.detail
                : i18n.t("errors.requestFailed", { status: request.status }),
            ),
          );
    request.onerror = () =>
      reject(new ApiError(0, i18n.t("data.importDialog.networkFailed")));
    request.send(form);
  });

export const fetchChanges = (signal?: AbortSignal) =>
  http.get<Change[]>(`${URL}/changes`, signal);

export const resolveChanges = (
  answers: { id: string; choice: ChangeChoice }[],
) => http.post<Change[]>(`${URL}/changes/resolve`, { answers });

export const fetchNetworking = (signal?: AbortSignal) =>
  http.get<Networking>(`${URL}/networking`, signal);

export const writeNetworking = (write: NetworkingWrite) =>
  http.post<Networking>(`${URL}/networking`, write);
