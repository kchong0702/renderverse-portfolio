import { http } from "@/shared/api/http";

export type AiProvider = "claude" | "openai" | "glm";
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
}

export interface Scheduling {
  work_day_start: string;
  work_day_end: string;
  meeting_gap_minutes: number;
}

export interface Connection {
  id: ConnectionId;
  status: "connected" | "not_connected";
}

export interface Settings {
  job_agent: JobAgent;
  automation: Automation;
  scheduling: Scheduling;
  ai_provider: AiProvider;
  connections: Connection[];
}

export interface SettingsPatch {
  job_agent?: Partial<JobAgent>;
  automation?: Partial<Automation>;
  scheduling?: Partial<Scheduling>;
  ai_provider?: AiProvider;
}

const URL = "/ops-api/v1/settings";

export const fetchSettings = (signal?: AbortSignal) =>
  http.get<Settings>(URL, signal);

export const updateSettings = (patch: SettingsPatch) =>
  http.patch<Settings>(URL, patch);
