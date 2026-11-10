import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

export type ModelFamily = "claude" | "glm" | "openai";
export type ConnectionId = "google" | "jsearch" | "portfolio_site";

export interface JobAgent {
  query: string;
  location: string;
  run_at: string;
  min_score: number;
}

export interface Automation {
  tailor_strong_matches: boolean;
  follow_up_reminders: boolean;
  suggest_replies: boolean;
  add_interview_invites: boolean;
  offer_free_slots: boolean;
}

export interface Scheduling {
  work_day_start: string;
  work_day_end: string;
  meeting_gap_minutes: number;
}

export interface SearchQuota {
  remaining: number;
  limit: number;
}

export interface Connection {
  id: ConnectionId;
  status: "connected" | "not_connected" | "not_configured";
  quota: SearchQuota | null;
  account: string | null;
}

export interface ModelChoice {
  family: ModelFamily;
  model: string;
}

export interface ModelCatalog {
  families: { family: ModelFamily; models: string[] }[];
}

export interface Settings {
  job_agent: JobAgent;
  automation: Automation;
  scheduling: Scheduling;
  ai_model: ModelChoice | null;
  connections: Connection[];
}

export interface SettingsPatch {
  job_agent?: Partial<JobAgent>;
  automation?: Partial<Automation>;
  scheduling?: Partial<Scheduling>;
  ai_model?: ModelChoice;
}

const URL = `${config.opsApiUrl}/settings`;

export const fetchSettings = (signal?: AbortSignal) =>
  http.get<Settings>(URL, signal);

export const updateSettings = (patch: SettingsPatch) =>
  http.patch<Settings>(URL, patch);

export const fetchModels = (signal?: AbortSignal) =>
  http.get<ModelCatalog>(`${URL}/models`, signal);

export const connectJsearch = (apiKey: string) =>
  http.put<Settings>(`${URL}/connections/jsearch`, { api_key: apiKey });

export const disconnectJsearch = () =>
  http.delete<Settings>(`${URL}/connections/jsearch`);
const GOOGLE_URL = "/ops-api/v1/integrations/google";

export const googleConnectUrl = (next: string) =>
  `${GOOGLE_URL}/connect?${new URLSearchParams({ next })}`;

export const disconnectGoogle = () => http.delete(GOOGLE_URL);
