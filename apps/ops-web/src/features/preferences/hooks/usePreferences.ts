import { useMutation, useQuery } from "@tanstack/react-query";
import {
  preferencesQueryOptions,
  updatePreferencesMutationOptions,
} from "../queries/preferences";

export function usePreferences() {
  return useQuery(preferencesQueryOptions);
}

export function useUpdatePreferences() {
  return useMutation(updatePreferencesMutationOptions);
}
