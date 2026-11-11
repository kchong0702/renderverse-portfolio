import {
  STAGES,
  type Application,
  type ApplicationStage,
} from "@/features/applications";
import { localDateTime } from "@/shared/lib/dates";

export const PERIODS = ["30d", "90d", "all"] as const;
export type Period = (typeof PERIODS)[number];

export const PERIOD_DAYS: Record<Period, number | null> = {
  "30d": 30,
  "90d": 90,
  all: null,
};

export function daysAgo(days: number): string {
  const at = new Date();
  at.setDate(at.getDate() - days);
  return localDateTime(at).slice(0, 10);
}

export function sentSince(
  applications: Application[],
  since: string | null,
): Application[] {
  return applications.filter(
    (a) =>
      a.stage !== "draft" &&
      (since === null || (a.applied_on !== null && a.applied_on >= since)),
  );
}

export function hasReached(
  application: Application,
  stage: ApplicationStage,
): boolean {
  return (
    application.stage !== "closed" &&
    STAGES.indexOf(application.stage) >= STAGES.indexOf(stage)
  );
}

export function lastEightWeeks(
  applications: Application[],
): { start: Date; sent: number; replied: number }[] {
  const now = new Date();
  const monday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() - ((now.getDay() + 6) % 7),
  );
  return Array.from({ length: 8 }, (_, index) => {
    const start = new Date(monday);
    start.setDate(monday.getDate() - (7 - index) * 7);
    const end = new Date(start);
    end.setDate(start.getDate() + 7);
    const [from, to] = [
      localDateTime(start).slice(0, 10),
      localDateTime(end).slice(0, 10),
    ];
    const sent = applications.filter(
      (a) =>
        a.stage !== "draft" &&
        a.applied_on !== null &&
        a.applied_on >= from &&
        a.applied_on < to,
    );
    return {
      start,
      sent: sent.length,
      replied: sent.filter((a) => hasReached(a, "replied")).length,
    };
  });
}
