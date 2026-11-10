import { useMutation, useQuery } from "@tanstack/react-query";
import {
  draftQueryOptions,
  makeLiveMutationOptions,
  publishMutationOptions,
  releasesQueryOptions,
} from "../queries/portfolio";

export function useDraft() {
  return useQuery(draftQueryOptions);
}

export function useReleases() {
  return useQuery(releasesQueryOptions);
}

export function usePublish() {
  return useMutation(publishMutationOptions);
}

export function useMakeLive() {
  return useMutation(makeLiveMutationOptions);
}
