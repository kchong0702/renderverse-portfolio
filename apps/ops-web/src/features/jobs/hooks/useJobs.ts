import { useMutation, useQuery } from "@tanstack/react-query";
import {
  analyseJobMutationOptions,
  findJobsMutationOptions,
  jobsQueryOptions,
  updateJobMutationOptions,
} from "../queries/jobs";

export function useJobs() {
  return useQuery(jobsQueryOptions);
}

export function useUpdateJob() {
  return useMutation(updateJobMutationOptions);
}

export function useFindJobs() {
  return useMutation(findJobsMutationOptions);
}

export function useAnalyseJob() {
  return useMutation(analyseJobMutationOptions);
}
