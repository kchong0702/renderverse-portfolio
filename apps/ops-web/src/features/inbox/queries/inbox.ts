import { queryOptions } from "@tanstack/react-query";
import { fetchInbox, fetchMessage } from "../api/inbox";

export const inboxQueryOptions = queryOptions({
  queryKey: ["inbox"],
  queryFn: ({ signal }) => fetchInbox(signal),
});

export const messageQueryOptions = (id: string) =>
  queryOptions({
    queryKey: ["inbox", id],
    queryFn: ({ signal }) => fetchMessage(id, signal),
    staleTime: Infinity,
  });
