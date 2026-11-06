import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { sessionQueryKey } from "@/shared/api/queryClient";
import {
  fetchMe,
  fetchSignInMethods,
  signInWithPassword,
  signOut,
} from "../api/auth";

export function useMe() {
  return useQuery({
    queryKey: sessionQueryKey,
    queryFn: ({ signal }) => fetchMe(signal),
    staleTime: Infinity,
  });
}

export function useSignInMethods() {
  return useQuery({
    queryKey: ["auth", "methods"],
    queryFn: ({ signal }) => fetchSignInMethods(signal),
    staleTime: Infinity,
  });
}

export function useSignIn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: signInWithPassword,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: sessionQueryKey }),
  });
}

export function useSignOut() {
  return useMutation({
    mutationFn: signOut,
    // A full reload drops every cached query along with the session
    onSuccess: () => window.location.assign("/sign-in"),
  });
}
