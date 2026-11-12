import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { isActive } from "../api/jobs";
import {
  analyseJobMutationOptions,
  findJobsMutationOptions,
  jobsQueryOptions,
  latestRunQueryOptions,
  updateJobMutationOptions,
  tailorJobMutationOptions,
} from "../queries/jobs";

export function useJobs() {
  return useQuery(jobsQueryOptions);
}

export function useLatestJobRun() {
  const client = useQueryClient();
  const run = useQuery(latestRunQueryOptions);
  const active = useRef(false);
  useEffect(() => {
    const now = isActive(run.data);
    if (active.current && !now)
      void client.invalidateQueries({ queryKey: jobsQueryOptions.queryKey });
    active.current = now;
  }, [run.data, client]);
  return run;
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

export function useTailorJob() {
  return useMutation(tailorJobMutationOptions);
}
