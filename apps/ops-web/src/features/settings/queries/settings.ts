import { mutationOptions, queryOptions } from "@tanstack/react-query";
import {
  connectJsearch,
  disconnectGoogle,
  disconnectJsearch,
  fetchIdentities,
  fetchModels,
  fetchSettings,
  unlinkIdentity,
  updateSettings,
  type Settings,
  type SettingsPatch,
} from "../api/settings";

const updateSettingsKey = ["settings", "update"] as const;

function applyPatch(settings: Settings, patch: SettingsPatch): Settings {
  return {
    ...settings,
    job_agent: { ...settings.job_agent, ...patch.job_agent },
    automation: { ...settings.automation, ...patch.automation },
    scheduling: { ...settings.scheduling, ...patch.scheduling },
    ai_model: patch.ai_model ?? settings.ai_model,
  };
}

export const settingsQueryOptions = queryOptions({
  queryKey: ["settings"],
  queryFn: ({ signal }) => fetchSettings(signal),
});

export const modelsQueryOptions = queryOptions({
  queryKey: ["settings", "models"],
  queryFn: ({ signal }) => fetchModels(signal),
});

export const updateSettingsMutationOptions = mutationOptions({
  mutationKey: updateSettingsKey,
  mutationFn: updateSettings,
  onMutate: async (patch, { client }) => {
    const { queryKey } = settingsQueryOptions;
    await client.cancelQueries({ queryKey });
    const previous = client.getQueryData(queryKey);
    if (previous) client.setQueryData(queryKey, applyPatch(previous, patch));
    return { previous };
  },
  onError: (_error, _patch, result, { client }) => {
    if (result?.previous)
      client.setQueryData(settingsQueryOptions.queryKey, result.previous);
  },
  onSuccess: (settings, _patch, _result, { client }) => {
    if (client.isMutating({ mutationKey: updateSettingsKey }) === 1)
      client.setQueryData(settingsQueryOptions.queryKey, settings);
  },
});

export const connectJsearchMutationOptions = mutationOptions({
  mutationFn: connectJsearch,
  onSuccess: (settings, _key, _result, { client }) =>
    client.setQueryData(settingsQueryOptions.queryKey, settings),
});

export const disconnectJsearchMutationOptions = mutationOptions({
  mutationFn: disconnectJsearch,
  onSuccess: (settings, _variables, _result, { client }) =>
    client.setQueryData(settingsQueryOptions.queryKey, settings),
});

export const disconnectGoogleMutationOptions = mutationOptions({
  mutationFn: disconnectGoogle,
  onSettled: (_data, _error, _variables, _result, { client }) =>
    client.invalidateQueries({ queryKey: settingsQueryOptions.queryKey }),
});

export const identitiesQueryOptions = queryOptions({
  queryKey: ["settings", "identities"],
  queryFn: ({ signal }) => fetchIdentities(signal),
});

export const unlinkIdentityMutationOptions = mutationOptions({
  mutationFn: unlinkIdentity,
  onSettled: (_data, _error, _variables, _result, { client }) =>
    client.invalidateQueries({ queryKey: identitiesQueryOptions.queryKey }),
});
