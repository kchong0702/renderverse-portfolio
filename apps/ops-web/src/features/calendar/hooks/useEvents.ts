import { useQuery } from "@tanstack/react-query";
import { eventsQueryOptions } from "../queries/calendar";

export function useEvents(from: Date, to: Date, enabled: boolean) {
  return useQuery({
    ...eventsQueryOptions(from.toISOString(), to.toISOString()),
    enabled,
  });
}
