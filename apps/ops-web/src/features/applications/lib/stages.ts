import type { Application, ApplicationStage } from "../api/applications";

export const STAGES: ApplicationStage[] = [
  "draft",
  "applied",
  "replied",
  "interview",
  "offer",
  "closed",
];

export function isDue({ stage, next_step_at }: Application): boolean {
  const endOfToday = new Date();
  endOfToday.setHours(23, 59, 59, 999);
  return (
    stage !== "closed" &&
    next_step_at !== null &&
    new Date(next_step_at) <= endOfToday
  );
}
