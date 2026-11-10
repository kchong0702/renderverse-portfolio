import type { Application } from "@/features/applications";
import type { CalendarEvent } from "../api/calendar";
import { eventTime, isoDay } from "./dates";

export type ItemKind = "interview" | "task" | "busy";

export interface CalendarItem {
  id: string;
  kind: ItemKind;
  title: string;
  step: string;
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
  applications: Application[],
): CalendarItem[] {
  return [
    ...events.map((event): CalendarItem => ({
      id: event.id,
      kind: event.interview ? "interview" : "busy",
      title: event.interview ? event.title : "",
      step: "",
      start: eventTime(event.start, event.all_day),
      end: eventTime(event.end, event.all_day),
      allDay: event.all_day,
    })),
    ...applications.flatMap(
      ({ id, company, stage, next_step, next_step_at }): CalendarItem[] =>
        next_step_at && stage !== "closed"
          ? [
              {
                id,
                kind: stage === "interview" ? "interview" : "task",
                title: company,
                step: next_step,
                start: new Date(next_step_at),
                end: new Date(next_step_at),
                allDay: false,
              },
            ]
          : [],
    ),
  ].sort((a, b) => a.start.getTime() - b.start.getTime());
}

export const onDay = (item: CalendarItem, day: Date) =>
  item.allDay
    ? isoDay(item.start) <= isoDay(day) && isoDay(day) < isoDay(item.end)
    : isoDay(item.start) === isoDay(day);
