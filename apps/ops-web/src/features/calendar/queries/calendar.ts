import { mutationOptions, queryOptions } from "@tanstack/react-query";
import { createEvent, fetchEvents } from "../api/calendar";

export const eventsQueryOptions = (from: string, to: string) =>
  queryOptions({
    queryKey: ["calendar", from, to],
    queryFn: ({ signal }) => fetchEvents(from, to, signal),
  });

export const createEventMutationOptions = mutationOptions({
  mutationFn: createEvent,
  onSuccess: (_data, _variables, _result, { client }) =>
    client.invalidateQueries({ queryKey: ["calendar"] }),
});
