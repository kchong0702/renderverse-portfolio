import { useMutation, useQuery } from "@tanstack/react-query";
import {
  addApplicationMutationOptions,
  addStepMutationOptions,
  applicationsQueryOptions,
  deleteApplicationMutationOptions,
  saveApplicationMutationOptions,
  saveStepMutationOptions,
  stepsBetweenQueryOptions,
  stepsQueryOptions,
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

export function useStepsBetween(start: Date, end: Date) {
  return useQuery(
    stepsBetweenQueryOptions(start.toISOString(), end.toISOString()),
  );
}

export function useSteps(applicationId: string) {
  return useQuery(stepsQueryOptions(applicationId));
}

export function useAddStep() {
  return useMutation(addStepMutationOptions);
}

export function useSaveStep() {
  return useMutation(saveStepMutationOptions);
}
