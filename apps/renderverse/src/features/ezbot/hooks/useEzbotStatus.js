import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { fetchHealth } from "@/features/ezbot/api/ezbot";
import { CONFIG } from "@/app/config";

export const CONNECTION_STATUS = {
  CONNECTING: "connecting",
  ONLINE: "online",
  OFFLINE: "offline",
};

export const ezbotKeys = {
  health: ["ezbot", "health"],
};

const STATUS_BY_QUERY = {
  pending: CONNECTION_STATUS.CONNECTING,
  success: CONNECTION_STATUS.ONLINE,
  error: CONNECTION_STATUS.OFFLINE,
};

export const useEzbotStatus = () => {
  const { status } = useQuery({
    queryKey: ezbotKeys.health,
    queryFn: ({ signal }) => fetchHealth(signal),
    enabled: CONFIG.isChatbotEnabled,
    staleTime: 30_000,
    retry: false,
  });
  return STATUS_BY_QUERY[status];
};

export const useRecheckEzbot = () => {
  const queryClient = useQueryClient();
  return useCallback(
    () => queryClient.invalidateQueries({ queryKey: ezbotKeys.health }),
    [queryClient],
  );
};
