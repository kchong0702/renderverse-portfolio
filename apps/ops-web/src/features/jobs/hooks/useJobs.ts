import { useMutation, useQuery } from "@tanstack/react-query";
import { jobsQueryOptions, updateJobMutationOptions } from "../queries/jobs";

export function useJobs() {
  return useQuery(jobsQueryOptions);
}

export function useUpdateJob() {
  return useMutation(updateJobMutationOptions);
}
