import { useQuery } from "@tanstack/react-query";
import { inboxQueryOptions, messageQueryOptions } from "../queries/inbox";

export function useInbox(enabled: boolean) {
  return useQuery({ ...inboxQueryOptions, enabled });
}

export function useMessage(id: string) {
  return useQuery(messageQueryOptions(id));
}
