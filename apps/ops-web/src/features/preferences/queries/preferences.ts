import { mutationOptions, queryOptions } from "@tanstack/react-query";
import {
  fetchPreferences,
  updatePreferences,
  type PreferencesPatch,
} from "../api/preferences";

const updatePreferencesKey = ["preferences", "update"] as const;

export const preferencesQueryOptions = queryOptions({
  queryKey: ["preferences"],
  queryFn: ({ signal }) => fetchPreferences(signal),
});

export const updatePreferencesMutationOptions = mutationOptions({
  mutationKey: updatePreferencesKey,
  mutationFn: updatePreferences,
  onMutate: async (patch: PreferencesPatch, { client }) => {
    const { queryKey } = preferencesQueryOptions;
    await client.cancelQueries({ queryKey });
    const previous = client.getQueryData(queryKey);
    if (previous) client.setQueryData(queryKey, { ...previous, ...patch });
    return { previous };
  },
  onError: (_error, _patch, result, { client }) => {
    if (result?.previous)
      client.setQueryData(preferencesQueryOptions.queryKey, result.previous);
  },
  onSuccess: (preferences, _patch, _result, { client }) => {
    if (client.isMutating({ mutationKey: updatePreferencesKey }) === 1)
      client.setQueryData(preferencesQueryOptions.queryKey, preferences);
  },
  onSettled: (_preferences, _error, _patch, _result, { client }) =>
    client.invalidateQueries({ queryKey: ["profile", "networking"] }),
});
