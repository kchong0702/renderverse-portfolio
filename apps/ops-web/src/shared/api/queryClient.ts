import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { ApiError } from "./http";

export const sessionQueryKey = ["me"] as const;

function isUnauthorized(error: Error): boolean {
  return error instanceof ApiError && error.status === 401;
}

function refreshSession(error: Error) {
  if (isUnauthorized(error))
    void queryClient.invalidateQueries({ queryKey: sessionQueryKey });
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.queryKey[0] !== sessionQueryKey[0]) refreshSession(error);
    },
  }),
  mutationCache: new MutationCache({ onError: refreshSession }),
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      retry: (failureCount, error) =>
        !(error instanceof ApiError && error.status < 500) && failureCount < 1,
      refetchOnWindowFocus: false,
    },
  },
});
