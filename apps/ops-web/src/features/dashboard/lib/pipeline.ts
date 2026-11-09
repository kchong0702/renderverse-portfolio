import {
  STAGES,
  type Application,
  type ApplicationStage,
} from "@/features/applications";

export const PERIODS = ["30d", "90d", "all"] as const;
export type Period = (typeof PERIODS)[number];

export const PERIOD_DAYS: Record<Period, number | null> = {
  "30d": 30,
  "90d": 90,
  all: null,
};

export interface Week {
  start: Date;
  sent: number;
}

function isoDay(at: Date): string {
  return new Date(at.getTime() - at.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 10);
}

export function daysAgo(days: number): string {
  const at = new Date();
  at.setDate(at.getDate() - days);
  return isoDay(at);
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

export function isDueSoon(
  application: Application,
): application is Application & { next_step_at: string } {
  const end = new Date();
  end.setDate(end.getDate() + 7);
  end.setHours(23, 59, 59, 999);
  return (
    application.stage !== "closed" &&
    application.next_step_at !== null &&
    new Date(application.next_step_at) <= end
  );
}

export function lastEightWeeks(applications: Application[]): Week[] {
  const monday = new Date();
  monday.setHours(0, 0, 0, 0);
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
  return Array.from({ length: 8 }, (_, index) => {
    const start = new Date(monday);
    start.setDate(monday.getDate() - (7 - index) * 7);
    const end = new Date(start);
    end.setDate(start.getDate() + 7);
    const [from, to] = [isoDay(start), isoDay(end)];
    return {
      start,
      sent: applications.filter(
        (a) =>
          a.stage !== "draft" &&
          a.applied_on !== null &&
          a.applied_on >= from &&
          a.applied_on < to,
      ).length,
    };
  });
}
