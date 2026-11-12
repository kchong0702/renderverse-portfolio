import type { Application, Step } from "@/features/applications";
import type { CalendarEvent } from "../api/calendar";
import { eventTime, isoDay } from "./dates";

export type ItemKind = "interview" | "task" | "busy";

export interface CalendarItem {
  id: string;
  kind: ItemKind;
  title: string;
  step: string;
  stepId: string | null;
  start: Date;
  end: Date;
  allDay: boolean;
}

export const itemTone: Record<ItemKind, string> = {
  interview: "bg-warn-bg border-amber text-ink",
  task: "bg-ok-bg border-ok text-ink",
  busy: "bg-chip border-hair text-ink-3",
};

export function itemsOf(
  events: CalendarEvent[],
  steps: Step[],
  applications: Application[],
  title: (step: Step) => string,
): CalendarItem[] {
  return [
    ...events.map((event): CalendarItem => ({
      id: event.id,
      kind: event.interview ? "interview" : "busy",
      title: event.interview ? event.title : "",
      step: "",
      stepId: null,
      start: eventTime(event.start, event.all_day),
      end: eventTime(event.end, event.all_day),
      allDay: event.all_day,
    })),
    ...steps.flatMap((step): CalendarItem[] => {
      const application = applications.find(
        ({ id }) => id === step.application_id,
      );
      const start = step.starts_at && new Date(step.starts_at);
      return start &&
        step.status !== "cancelled" &&
        application?.stage !== "closed" &&
        !events.some(
          (event) =>
            event.interview &&
            eventTime(event.start, event.all_day).getTime() === start.getTime(),
        )
        ? [
            {
              id: step.id,
              kind: step.kind === "interview" ? "interview" : "task",
              title: application?.company ?? title(step),
              step: application ? title(step) : "",
              stepId: step.id,
              start,
              end: start,
              allDay: false,
            },
          ]
        : [];
    }),
  ].sort((a, b) => a.start.getTime() - b.start.getTime());
}

export const onDay = (item: CalendarItem, day: Date) =>
  item.allDay
    ? isoDay(item.start) <= isoDay(day) && isoDay(day) < isoDay(item.end)
    : isoDay(item.start) === isoDay(day);
