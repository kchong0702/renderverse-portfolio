import { mutationOptions, queryOptions } from "@tanstack/react-query";
import {
  fetchChanges,
  fetchImports,
  fetchNetworking,
  importFile,
  resolveChanges,
  writeNetworking,
} from "../api/data";

export const importsQueryOptions = queryOptions({
  queryKey: ["profile", "imports"],
  queryFn: ({ signal }) => fetchImports(signal),
});

export const changesQueryOptions = queryOptions({
  queryKey: ["profile", "changes"],
  queryFn: ({ signal }) => fetchChanges(signal),
});

export const networkingQueryOptions = queryOptions({
  queryKey: ["profile", "networking"],
  queryFn: ({ signal }) => fetchNetworking(signal),
});

export const importFileMutationOptions = mutationOptions({
  mutationFn: ({ file, onSent }: { file: File; onSent: () => void }) =>
    importFile(file, onSent),
  onSettled: (_import, _error, _upload, _result, { client }) =>
    Promise.all([
      client.invalidateQueries({ queryKey: ["profile"] }),
      client.invalidateQueries({ queryKey: ["portfolio"] }),
    ]),
});

export const resolveChangesMutationOptions = mutationOptions({
  mutationFn: resolveChanges,
  onSuccess: (pending, _answers, _result, { client }) =>
    client.setQueryData(changesQueryOptions.queryKey, pending),
  onSettled: (_pending, _error, _answers, _result, { client }) =>
    Promise.all([
      client.invalidateQueries({ queryKey: ["profile"] }),
      client.invalidateQueries({ queryKey: ["portfolio"] }),
    ]),
});

export const writeNetworkingMutationOptions = mutationOptions({
  mutationFn: writeNetworking,
  onSuccess: (networking, _write, _result, { client }) =>
    client.setQueryData(networkingQueryOptions.queryKey, networking),
});
