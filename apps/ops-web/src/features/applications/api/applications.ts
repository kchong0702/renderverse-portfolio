import { http } from "@/shared/api/http";

export type ApplicationStage =
  "draft" | "applied" | "replied" | "interview" | "offer" | "closed";

export interface ApplicationWrite {
  company: string;
  role: string;
  stage: ApplicationStage;
  applied_on: string | null;
  next_step: string;
  next_step_at: string | null;
}

export interface ApplicationCreate extends ApplicationWrite {
  job_id: string | null;
}

export interface Application extends ApplicationCreate {
  id: string;
  fit: number | null;
}

const URL = "/ops-api/v1/applications";

export const fetchApplications = (signal?: AbortSignal) =>
  http.get<Application[]>(URL, signal);

export const addApplication = (application: ApplicationCreate) =>
  http.post<Application>(URL, application);

export const saveApplication = ({ id, ...application }: Application) =>
  http.put<Application>(`${URL}/${id}`, application);

export const deleteApplication = (id: string) => http.delete(`${URL}/${id}`);
