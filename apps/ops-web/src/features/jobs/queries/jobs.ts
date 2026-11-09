import { mutationOptions, queryOptions } from "@tanstack/react-query";
import { fetchJobs, updateJob, type JobUpdate } from "../api/jobs";

export const jobsQueryOptions = queryOptions({
  queryKey: ["jobs"],
  queryFn: ({ signal }) => fetchJobs(signal),
});

export const updateJobMutationOptions = mutationOptions({
  mutationFn: updateJob,
  onMutate: async ({ id, status }: JobUpdate, { client }) => {
    const { queryKey } = jobsQueryOptions;
    await client.cancelQueries({ queryKey });
    const previous = client.getQueryData(queryKey);
    if (previous)
      client.setQueryData(
        queryKey,
        previous.map((job) => (job.id === id ? { ...job, status } : job)),
      );
    return { previous };
  },
  onError: (_error, _update, result, { client }) => {
    if (result?.previous)
      client.setQueryData(jobsQueryOptions.queryKey, result.previous);
  },
  onSettled: (_job, _error, _update, _result, { client }) =>
    client.invalidateQueries({ queryKey: jobsQueryOptions.queryKey }),
});
