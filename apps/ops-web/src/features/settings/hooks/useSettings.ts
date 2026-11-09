import { useMutation, useQuery } from "@tanstack/react-query";
import {
  connectJsearchMutationOptions,
  disconnectGoogleMutationOptions,
  disconnectJsearchMutationOptions,
  modelsQueryOptions,
  settingsQueryOptions,
  updateSettingsMutationOptions,
} from "../queries/settings";

export function useSettings() {
  return useQuery(settingsQueryOptions);
}

export function useUpdateSettings() {
  return useMutation(updateSettingsMutationOptions);
}

export function useModels() {
  return useQuery(modelsQueryOptions);
}

export function useConnectJsearch() {
  return useMutation(connectJsearchMutationOptions);
}

export function useDisconnectJsearch() {
  return useMutation(disconnectJsearchMutationOptions);
}

export function useDisconnectGoogle() {
  return useMutation(disconnectGoogleMutationOptions);
}
