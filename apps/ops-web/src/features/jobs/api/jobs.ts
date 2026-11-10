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
  seen_at: string | null;
}

export interface JobList {
  jobs: Job[];
  new_count: number;
}

export type RunResult<R> =
  { status: "completed"; reply: R } | { status: "failed"; reason: string };

export interface JobUpdate {
  id: string;
  status?: JobStatus;
  seen?: true;
}

const URL = "/ops-api/v1/jobs";

export const fetchJobs = (signal?: AbortSignal) =>
  http.get<JobList>(URL, signal);

export const updateJob = ({ id, ...patch }: JobUpdate) =>
  http.patch<Job>(`${URL}/${id}`, patch);

export const findJobs = () => http.post<RunResult<Job[]>>(`${URL}/find`);

export const analyseJob = (id: string) =>
  http.post<RunResult<Job>>(`${URL}/${id}/analyse`);
