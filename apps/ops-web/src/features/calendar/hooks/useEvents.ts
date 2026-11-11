import { useMutation, useQuery } from "@tanstack/react-query";
import {
  createEventMutationOptions,
  eventsQueryOptions,
  freeSlotsQueryOptions,
} from "../queries/calendar";

export function useEvents(from: Date, to: Date, enabled: boolean) {
  return useQuery({
    ...eventsQueryOptions(from.toISOString(), to.toISOString()),
    enabled,
  });
}

export function useFreeSlots(enabled: boolean) {
  return useQuery({ ...freeSlotsQueryOptions, enabled });
}

export function useCreateEvent() {
  return useMutation(createEventMutationOptions);
}
