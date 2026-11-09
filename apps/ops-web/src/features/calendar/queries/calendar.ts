import { queryOptions } from "@tanstack/react-query";
import { fetchEvents } from "../api/calendar";

export const eventsQueryOptions = (from: string, to: string) =>
  queryOptions({
    queryKey: ["calendar", from, to],
    queryFn: ({ signal }) => fetchEvents(from, to, signal),
  });
