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
