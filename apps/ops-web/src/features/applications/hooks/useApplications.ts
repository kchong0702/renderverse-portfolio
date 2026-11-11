import { useMutation, useQuery } from "@tanstack/react-query";
import {
  addApplicationMutationOptions,
  applicationsQueryOptions,
  deleteApplicationMutationOptions,
  saveApplicationMutationOptions,
} from "../queries/applications";

export function useApplications() {
  return useQuery(applicationsQueryOptions);
}

export function useAddApplication() {
  return useMutation(addApplicationMutationOptions);
}

export function useSaveApplication() {
  return useMutation(saveApplicationMutationOptions);
}

export function useDeleteApplication() {
  return useMutation(deleteApplicationMutationOptions);
}
