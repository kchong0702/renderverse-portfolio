import {
  mutationOptions,
  queryOptions,
  type QueryClient,
} from "@tanstack/react-query";
import {
  addApplication,
  deleteApplication,
  fetchApplications,
  saveApplication,
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
    client.invalidateQueries({ queryKey: applicationsQueryOptions.queryKey }),
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
    client.invalidateQueries({ queryKey: applicationsQueryOptions.queryKey }),
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
});
