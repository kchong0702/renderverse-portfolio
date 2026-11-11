import { useMutation, useQuery } from "@tanstack/react-query";
import {
  meQueryOptions,
  signInMethodsQueryOptions,
  signInMutationOptions,
  signOutMutationOptions,
} from "../queries/auth";

export function useMe() {
  return useQuery(meQueryOptions);
}

export function useIsAdmin() {
  return useMe().data?.role === "admin";
}

export function useSignInMethods() {
  return useQuery(signInMethodsQueryOptions);
}

export function useSignIn() {
  return useMutation(signInMutationOptions);
}

export function useSignOut() {
  return useMutation(signOutMutationOptions);
}
