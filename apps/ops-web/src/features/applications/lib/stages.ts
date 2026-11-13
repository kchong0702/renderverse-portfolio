import type { TFunction } from "i18next";
import { daysFromToday, daysLeftThisWeek } from "@/shared/lib/dates";
import type { Application, ApplicationStage, Step } from "../api/applications";

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
  overdue,
}: Application): number | null {
  if (stage !== "applied" || next_step || overdue.length > 0 || !applied_on)
    return null;
  const days = -daysFromToday(applied_on);
  return days >= 7 ? days : null;
}

export function isStepDue(
  application: Application,
  days: number,
): application is Application & { next_step: Step & { starts_at: string } } {
  const end = new Date();
  end.setDate(end.getDate() + days);
  end.setHours(23, 59, 59, 999);
  return (
    application.stage !== "closed" &&
    application.next_step?.starts_at != null &&
    new Date(application.next_step.starts_at) <= end
  );
}

export function isDue(application: Application): boolean {
  return (
    followUpDays(application) !== null ||
    isStepDue(application, 0) ||
    (application.stage !== "closed" &&
      (application.overdue.length > 0 ||
        (application.next_step?.due_on != null &&
          daysFromToday(application.next_step.due_on) <= daysLeftThisWeek())))
  );
}

export const stepTitle = (step: Step, t: TFunction) =>
  step.title || t(`applications.steps.kinds.${step.kind}`);
