import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

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
    `${config.opsApiUrl}/calendar?${new URLSearchParams({ from, to })}`,
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
  http.get<FreeSlots>(`${config.opsApiUrl}/calendar/free-slots`, signal);

export const createEvent = (event: EventCreate) =>
  http.post<CalendarEvent>(`${config.opsApiUrl}/calendar/events`, event);
