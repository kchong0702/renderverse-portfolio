import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

export type ApplicationStage =
  "draft" | "applied" | "replied" | "interview" | "offer" | "closed";

export type NextStepFormat = "video" | "phone" | "on_site";

export interface ApplicationWrite {
  company: string;
  role: string;
  stage: ApplicationStage;
  applied_on: string | null;
  next_step: string;
  next_step_at: string | null;
  next_step_due: string | null;
  next_step_format: NextStepFormat | null;
  next_step_location: string | null;
}

export interface ApplicationCreate extends ApplicationWrite {
  job_id: string | null;
}

export interface Application extends ApplicationCreate {
  id: string;
  fit: number | null;
}

const URL = `${config.opsApiUrl}/applications`;

export const fetchApplications = (signal?: AbortSignal) =>
  http.get<Application[]>(URL, signal);

export const addApplication = (application: ApplicationCreate) =>
  http.post<Application>(URL, application);

export const saveApplication = ({
  id,
  company,
  role,
  stage,
  applied_on,
  next_step,
  next_step_at,
  next_step_due,
  next_step_format,
  next_step_location,
}: { id: string } & ApplicationWrite) =>
  http.put<Application>(`${URL}/${id}`, {
    company,
    role,
    stage,
    applied_on,
    next_step,
    next_step_at,
    next_step_due,
    next_step_format,
    next_step_location,
  });

export const deleteApplication = (id: string) => http.delete(`${URL}/${id}`);
