import { useMutation, useQuery } from "@tanstack/react-query";
import {
  createEventMutationOptions,
  eventsQueryOptions,
} from "../queries/calendar";

export function useEvents(from: Date, to: Date, enabled: boolean) {
  return useQuery({
    ...eventsQueryOptions(from.toISOString(), to.toISOString()),
    enabled,
  });
}

export function useCreateEvent() {
  return useMutation(createEventMutationOptions);
}
