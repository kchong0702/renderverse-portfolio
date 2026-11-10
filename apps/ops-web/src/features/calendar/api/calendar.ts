import { http } from "@/shared/api/http";

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  location: string;
  url: string;
  interview: boolean;
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

export interface FreeSlots {
  free_slots: { start: string; end: string }[];
  timezone: string;
}

export const fetchFreeSlots = (signal?: AbortSignal) =>
  http.get<FreeSlots>("/ops-api/v1/calendar/free-slots", signal);

export const createEvent = (event: EventCreate) =>
  http.post<CalendarEvent>("/ops-api/v1/calendar/events", event);
