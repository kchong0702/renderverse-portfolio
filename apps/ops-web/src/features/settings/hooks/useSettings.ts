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

export function useGoogleAccount() {
  const settings = useSettings();
  const google = settings.data?.connections.find(({ id }) => id === "google");
  return {
    settings,
    account: google?.status === "connected" ? google.account : null,
    problem:
      google?.status === "not_configured"
        ? ("not_configured" as const)
        : ("not_connected" as const),
  };
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
