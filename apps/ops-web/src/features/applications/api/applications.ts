import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

export type ApplicationStage =
  "draft" | "applied" | "replied" | "interview" | "offer" | "closed";

export type NextStepFormat = "video" | "phone" | "on_site";

export type StepKind =
  "interview" | "follow_up" | "take_home" | "offer_deadline";

export type StepStatus = "open" | "done" | "cancelled";

export interface ApplicationWrite {
  stage: ApplicationStage;
  applied_on: string | null;
}

export interface ApplicationUpdate extends ApplicationWrite {
  company: string;
  role: string;
}

export type ApplicationCreate = ApplicationWrite &
  (
    | { job_id: string }
    | { company: string; role: string; url: string; location: string }
  );

export interface StepWrite {
  kind: StepKind;
  title: string;
  starts_at: string | null;
  ends_at: string | null;
  due_on: string | null;
  format: NextStepFormat | null;
  location: string | null;
  status: StepStatus;
}

export interface Step extends StepWrite {
  id: string;
  application_id: string | null;
  email_thread_id: string | null;
}

export interface Application extends ApplicationUpdate {
  id: string;
  job_id: string;
  by_hand: boolean;
  fit: number | null;
  next_step: Step | null;
  overdue: Step[];
  offer_deadline: string | null;
}

const URL = `${config.opsApiUrl}/applications`;

export const fetchApplications = (signal?: AbortSignal) =>
  http.get<Application[]>(URL, signal);

export const addApplication = (application: ApplicationCreate) =>
  http.post<Application>(URL, application);

export const saveApplication = ({
  id,
  stage,
  applied_on,
  company,
  role,
  by_hand,
}: { id: string; by_hand: boolean } & ApplicationUpdate) =>
  http.put<Application>(
    `${URL}/${id}`,
    by_hand ? { stage, applied_on, company, role } : { stage, applied_on },
  );

export const deleteApplication = (id: string) => http.delete(`${URL}/${id}`);

export const fetchStepsBetween = (
  start: string,
  end: string,
  signal?: AbortSignal,
) =>
  http.get<Step[]>(
    `${URL}/steps?${new URLSearchParams({ start, end })}`,
    signal,
  );

export const fetchSteps = (applicationId: string, signal?: AbortSignal) =>
  http.get<Step[]>(`${URL}/${applicationId}/steps`, signal);

export const addStep = ({
  applicationId,
  step,
}: {
  applicationId: string;
  step: StepWrite;
}) => http.post<Step>(`${URL}/${applicationId}/steps`, step);

export const saveStep = ({ id, ...step }: Step) =>
  http.put<Step>(`${URL}/steps/${id}`, step);
