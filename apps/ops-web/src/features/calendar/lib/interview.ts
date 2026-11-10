import type { CalendarEvent } from "../api/calendar";

export const isInterview = (event: CalendarEvent) =>
  /interview|screen|hiring|recruit/i.test(event.title);
