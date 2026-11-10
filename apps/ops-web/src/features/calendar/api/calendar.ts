import { http } from "@/shared/api/http";

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  location: string;
  url: string;
}

export const fetchEvents = (from: string, to: string, signal?: AbortSignal) =>
  http.get<CalendarEvent[]>(
    `/ops-api/v1/calendar?${new URLSearchParams({ from, to })}`,
    signal,
  );

export interface EventCreate {
  title: string;
  start: string;
  end: string;
  location?: string;
}

export const createEvent = (event: EventCreate) =>
  http.post<CalendarEvent>("/ops-api/v1/calendar/events", event);
