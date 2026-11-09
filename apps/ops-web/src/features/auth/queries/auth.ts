import { mutationOptions, queryOptions } from "@tanstack/react-query";
import { sessionQueryKey } from "@/shared/api/queryClient";
import {
  fetchMe,
  fetchSignInMethods,
  signInWithPassword,
  signOut,
} from "../api/auth";

export const meQueryOptions = queryOptions({
  queryKey: sessionQueryKey,
  queryFn: ({ signal }) => fetchMe(signal),
  staleTime: Infinity,
});

export const signInMethodsQueryOptions = queryOptions({
  queryKey: ["auth", "methods"],
  queryFn: ({ signal }) => fetchSignInMethods(signal),
  staleTime: Infinity,
});

export const signInMutationOptions = mutationOptions({
  mutationFn: signInWithPassword,
  onSuccess: (_data, _body, _result, { client }) =>
    client.invalidateQueries({ queryKey: sessionQueryKey }),
});

export const signOutMutationOptions = mutationOptions({
  mutationFn: signOut,
  onSuccess: () => window.location.assign("/sign-in"),
});
