import {
  mutationOptions,
  queryOptions,
  type QueryClient,
} from "@tanstack/react-query";
import { jobsQueryOptions } from "@/features/jobs";
import {
  addApplication,
  addStep,
  deleteApplication,
  fetchApplications,
  fetchSteps,
  fetchStepsBetween,
  saveApplication,
  saveStep,
  type Application,
} from "../api/applications";

export const applicationsQueryOptions = queryOptions({
  queryKey: ["applications"],
  queryFn: ({ signal }) => fetchApplications(signal),
});

async function changeApplications(
  client: QueryClient,
  change: (applications: Application[]) => Application[],
) {
  const { queryKey } = applicationsQueryOptions;
  await client.cancelQueries({ queryKey });
  const previous = client.getQueryData(queryKey);
  if (previous) client.setQueryData(queryKey, change(previous));
  return { previous };
}

export const addApplicationMutationOptions = mutationOptions({
  mutationFn: addApplication,
  onSettled: (_application, _error, _create, _result, { client }) =>
    Promise.all([
      client.invalidateQueries({ queryKey: applicationsQueryOptions.queryKey }),
      client.invalidateQueries({ queryKey: jobsQueryOptions.queryKey }),
    ]),
});

export const saveApplicationMutationOptions = mutationOptions({
  mutationFn: saveApplication,
  onMutate: (application: Application, { client }) =>
    changeApplications(client, (applications) =>
      applications.map((a) => (a.id === application.id ? application : a)),
    ),
  onError: (_error, _application, result, { client }) => {
    if (result?.previous)
      client.setQueryData(applicationsQueryOptions.queryKey, result.previous);
  },
  onSettled: (_saved, _error, _application, _result, { client }) =>
    Promise.all([
      client.invalidateQueries({ queryKey: applicationsQueryOptions.queryKey }),
      client.invalidateQueries({ queryKey: jobsQueryOptions.queryKey }),
    ]),
});

export const deleteApplicationMutationOptions = mutationOptions({
  mutationFn: deleteApplication,
  onMutate: (id: string, { client }) =>
    changeApplications(client, (applications) =>
      applications.filter((a) => a.id !== id),
    ),
  onError: (_error, _id, result, { client }) => {
    if (result?.previous)
      client.setQueryData(applicationsQueryOptions.queryKey, result.previous);
  },
  onSettled: (_deleted, _error, _id, _result, { client }) =>
    Promise.all([
      client.invalidateQueries({ queryKey: jobsQueryOptions.queryKey }),
      client.invalidateQueries({
        queryKey: [...applicationsQueryOptions.queryKey, "steps"],
      }),
    ]),
});

export const stepsBetweenQueryOptions = (start: string, end: string) =>
  queryOptions({
    queryKey: [...applicationsQueryOptions.queryKey, "steps", start, end],
    queryFn: ({ signal }) => fetchStepsBetween(start, end, signal),
  });

export const stepsQueryOptions = (applicationId: string) =>
  queryOptions({
    queryKey: [...applicationsQueryOptions.queryKey, applicationId, "steps"],
    queryFn: ({ signal }) => fetchSteps(applicationId, signal),
  });

export const addStepMutationOptions = mutationOptions({
  mutationFn: addStep,
  onSettled: (_step, _error, _add, _result, { client }) =>
    client.invalidateQueries({ queryKey: applicationsQueryOptions.queryKey }),
});

export const saveStepMutationOptions = mutationOptions({
  mutationFn: saveStep,
  onSettled: (_step, _error, _save, _result, { client }) =>
    client.invalidateQueries({ queryKey: applicationsQueryOptions.queryKey }),
});
