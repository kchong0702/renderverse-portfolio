import { ApiError, http } from "@/shared/api/http";
import { config } from "@/shared/config";

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

export type PostedWithin = "day" | "week" | "month";

export interface JobSearch {
  query: string | null;
  location: string | null;
  posted_within: PostedWithin | null;
}

export type RunTrigger = "scheduled" | "manual" | "agent";
export type RunStatus = "queued" | "running" | "done" | "failed";

export interface JobRun {
  id: string;
  trigger: RunTrigger;
  status: RunStatus;
  run_after: string;
  found: number;
  new: number;
  matched: number;
  error: string;
  created_at: string;
  finished_at: string | null;
}

export const isActive = (run: JobRun | null | undefined) =>
  run?.status === "running" ||
  (run?.status === "queued" && Date.parse(run.run_after) <= Date.now());

export interface TailoredDocument {
  document_id: string;
  tailoring: boolean;
}

export interface TailorResult {
  resume: TailoredDocument;
  cover_letter: TailoredDocument | null;
}

export interface JobUpdate {
  id: string;
  status?: JobStatus;
  seen?: true;
}

const URL = `${config.opsApiUrl}/jobs`;

export const fetchJobs = (signal?: AbortSignal) =>
  http.get<JobList>(URL, signal);

export const fetchLatestRun = (signal?: AbortSignal) =>
  http.get<JobRun>(`${URL}/runs/latest`, signal).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  });

export const updateJob = ({ id, ...patch }: JobUpdate) =>
  http.patch<Job>(`${URL}/${id}`, patch);

export const findJobs = (search: JobSearch) =>
  http.post<JobRun>(`${URL}/find`, search);

export const analyseJob = (id: string) =>
  http.post<Job>(`${URL}/${id}/analyse`);

export const tailorJob = (id: string) =>
  http.post<TailorResult>(`${URL}/${id}/tailor`);
