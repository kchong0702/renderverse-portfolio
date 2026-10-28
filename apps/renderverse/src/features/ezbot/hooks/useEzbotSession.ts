import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { createSession } from "@/features/ezbot/api/session/session";
import { CONFIG } from "@/app/config";

export const CONNECTION_STATUS = {
  CONNECTING: "connecting",
  ONLINE: "online",
  OFFLINE: "offline",
} as const;

export type ConnectionStatus =
  (typeof CONNECTION_STATUS)[keyof typeof CONNECTION_STATUS];

export const ezbotKeys = {
  session: ["ezbot", "session"],
} as const;

const STATUS_BY_QUERY: Record<
  "pending" | "success" | "error",
  ConnectionStatus
> = {
  pending: CONNECTION_STATUS.CONNECTING,
  success: CONNECTION_STATUS.ONLINE,
  error: CONNECTION_STATUS.OFFLINE,
};

export const useEzbotStatus = () => {
  const { status } = useQuery({
    queryKey: ezbotKeys.session,
    queryFn: ({ signal }) => createSession(signal),
    enabled: CONFIG.isChatbotEnabled,
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: 1,
  });
  return STATUS_BY_QUERY[status];
};

export const useRenewEzbotSession = () => {
  const queryClient = useQueryClient();
  return useCallback(
    () => queryClient.refetchQueries({ queryKey: ezbotKeys.session }),
    [queryClient],
  );
};

export const useRecheckEzbot = () => {
  const queryClient = useQueryClient();
  return useCallback(() => {
    if (queryClient.getQueryState(ezbotKeys.session)?.status === "error") {
      queryClient.refetchQueries({ queryKey: ezbotKeys.session });
    }
  }, [queryClient]);
};
