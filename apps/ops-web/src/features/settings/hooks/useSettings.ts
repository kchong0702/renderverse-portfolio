import { useMutation, useQuery } from "@tanstack/react-query";
import {
  settingsQueryOptions,
  updateSettingsMutationOptions,
} from "../queries/settings";

export function useSettings() {
  return useQuery(settingsQueryOptions);
}

export function useUpdateSettings() {
  return useMutation(updateSettingsMutationOptions);
}
