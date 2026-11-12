import { useMutation, useQuery } from "@tanstack/react-query";
import {
  changesQueryOptions,
  importFileMutationOptions,
  importsQueryOptions,
  networkingQueryOptions,
  resolveChangesMutationOptions,
  writeNetworkingMutationOptions,
} from "../queries/data";

export function useImports() {
  return useQuery(importsQueryOptions);
}

export function useImportFile() {
  return useMutation(importFileMutationOptions);
}

export function useChanges() {
  return useQuery(changesQueryOptions);
}

export function useResolveChanges() {
  return useMutation(resolveChangesMutationOptions);
}

export function useNetworking() {
  return useQuery(networkingQueryOptions);
}

export function useWriteNetworking() {
  return useMutation(writeNetworkingMutationOptions);
}
