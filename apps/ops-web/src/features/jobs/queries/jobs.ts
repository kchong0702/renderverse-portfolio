import { mutationOptions, queryOptions } from "@tanstack/react-query";
import { documentsQueryOptions } from "@/features/documents";
import {
  analyseJob,
  fetchJobs,
  fetchLatestRun,
  findJobs,
  isActive,
  tailorJob,
  updateJob,
  type JobUpdate,
} from "../api/jobs";

export const jobsQueryOptions = queryOptions({
  queryKey: ["jobs"],
  queryFn: ({ signal }) => fetchJobs(signal),
});

export const latestRunQueryOptions = queryOptions({
  queryKey: ["jobs", "runs", "latest"],
  queryFn: ({ signal }) => fetchLatestRun(signal),
  refetchInterval: ({ state }) => (isActive(state.data) ? 2000 : false),
});

export const updateJobMutationOptions = mutationOptions({
  mutationFn: updateJob,
  onMutate: async ({ id, status }: JobUpdate, { client }) => {
    const { queryKey } = jobsQueryOptions;
    await client.cancelQueries({ queryKey });
    const previous = client.getQueryData(queryKey);
    if (previous)
      client.setQueryData(queryKey, {
        ...previous,
        jobs: previous.jobs.map((job) =>
          job.id === id && status ? { ...job, status } : job,
        ),
      });
    return { previous };
  },
  onError: (_error, _update, result, { client }) => {
    if (result?.previous)
      client.setQueryData(jobsQueryOptions.queryKey, result.previous);
  },
  onSettled: (_job, _error, _update, _result, { client }) =>
    client.invalidateQueries({ queryKey: jobsQueryOptions.queryKey }),
});

export const findJobsMutationOptions = mutationOptions({
  mutationKey: ["jobs", "find"],
  mutationFn: findJobs,
  onMutate: (_search, { client }) =>
    client.cancelQueries({ queryKey: latestRunQueryOptions.queryKey }),
  onSuccess: (run, _variables, _result, { client }) =>
    client.setQueryData(latestRunQueryOptions.queryKey, run),
});

export const analyseJobMutationOptions = mutationOptions({
  mutationKey: ["jobs", "analyse"],
  mutationFn: analyseJob,
  onSettled: (_run, _error, _id, _result, { client }) =>
    client.invalidateQueries({ queryKey: jobsQueryOptions.queryKey }),
});

export const tailorJobMutationOptions = mutationOptions({
  mutationKey: ["jobs", "tailor"],
  mutationFn: tailorJob,
  onSettled: (_tailored, _error, _id, _result, { client }) =>
    client.invalidateQueries({
      queryKey: documentsQueryOptions.queryKey,
      exact: true,
    }),
});
