import { http } from "@/shared/api/http";

export type JobStatus = "picked" | "saved" | "dismissed";
export type Importance = "required" | "nice_to_have";
export type Match = "met" | "partly" | "not_met";
export type FitBand = "excellent" | "good" | "possible" | "poor";

export interface Requirement {
  text: string;
  importance: Importance;
  match: Match;
  reason: string;
}

export interface FitAnalysis {
  fit: number;
  band: FitBand;
  requirements: Requirement[];
}

export interface Job {
  id: string;
  external_id: string | null;
  source: string;
  title: string;
  company: string;
  location: string;
  salary: string;
  url: string;
  posted_at: string | null;
  status: JobStatus;
  analysis: FitAnalysis | null;
}

export interface JobUpdate {
  id: string;
  status: JobStatus;
}

const URL = "/ops-api/v1/jobs";

export const fetchJobs = (signal?: AbortSignal) => http.get<Job[]>(URL, signal);

export const updateJob = ({ id, ...patch }: JobUpdate) =>
  http.patch<Job>(`${URL}/${id}`, patch);
