import { daysFromToday } from "@/shared/lib/dates";
import type { Application, ApplicationStage } from "../api/applications";

export const STAGES: ApplicationStage[] = [
  "draft",
  "applied",
  "replied",
  "interview",
  "offer",
  "closed",
];

export function followUpDays({
  stage,
  applied_on,
  next_step,
  next_step_at,
}: Application): number | null {
  if (stage !== "applied" || next_step || next_step_at || !applied_on)
    return null;
  const days = -daysFromToday(applied_on);
  return days >= 7 ? days : null;
}

export function isDue(application: Application): boolean {
  const endOfToday = new Date();
  endOfToday.setHours(23, 59, 59, 999);
  return (
    followUpDays(application) !== null ||
    (application.stage !== "closed" &&
      application.next_step_at !== null &&
      new Date(application.next_step_at) <= endOfToday)
  );
}
