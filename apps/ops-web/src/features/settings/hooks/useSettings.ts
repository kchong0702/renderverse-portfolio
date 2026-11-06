import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchSettings,
  updateSettings,
  type Settings,
  type SettingsPatch,
} from "../api/settings";

const settingsKey = ["settings"] as const;
const updateKey = ["settings", "update"] as const;

function applyPatch(settings: Settings, patch: SettingsPatch): Settings {
  return {
    ...settings,
    job_agent: { ...settings.job_agent, ...patch.job_agent },
    automation: { ...settings.automation, ...patch.automation },
    scheduling: { ...settings.scheduling, ...patch.scheduling },
    ai_provider: patch.ai_provider ?? settings.ai_provider,
  };
}

export function useSettings() {
  return useQuery({
    queryKey: settingsKey,
    queryFn: ({ signal }) => fetchSettings(signal),
  });
}

/** Saves a change and shows it at once; a failed save puts the old value back */
export function useUpdateSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: updateKey,
    mutationFn: updateSettings,
    onMutate: async (patch) => {
      await queryClient.cancelQueries({ queryKey: settingsKey });
      const previous = queryClient.getQueryData<Settings>(settingsKey);
      if (previous)
        queryClient.setQueryData(settingsKey, applyPatch(previous, patch));
      return { previous };
    },
    onError: (_error, _patch, context) => {
      if (context?.previous)
        queryClient.setQueryData(settingsKey, context.previous);
    },
    onSuccess: (settings) => {
      // Only the last save in flight may overwrite, or it would undo newer changes
      if (queryClient.isMutating({ mutationKey: updateKey }) === 1) {
        queryClient.setQueryData(settingsKey, settings);
      }
    },
  });
}
