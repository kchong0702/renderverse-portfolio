import { http } from "@/shared/api/http";

export type ChangeKind = "about" | "skill" | "project";
export type ChangeType = "added" | "changed" | "removed";

export interface Change {
  kind: ChangeKind;
  id: string | null;
  name: string;
  change: ChangeType;
}

export interface Draft {
  site_url: string | null;
  number: number;
  changes: Change[];
}

export interface Release {
  id: string;
  number: number;
  published_at: string;
  live: boolean;
}

const URL = "/ops-api/v1/portfolio";

export const fetchDraft = (signal?: AbortSignal) =>
  http.get<Draft>(`${URL}/draft`, signal);

export const fetchReleases = (signal?: AbortSignal) =>
  http.get<Release[]>(`${URL}/releases`, signal);

export const publishRelease = () => http.post<Release>(`${URL}/releases`);

export const makeReleaseLive = (id: string) =>
  http.post<Release>(`${URL}/releases/${id}/live`);
