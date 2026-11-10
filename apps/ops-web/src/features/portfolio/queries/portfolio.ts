import { mutationOptions, queryOptions } from "@tanstack/react-query";
import {
  fetchDraft,
  fetchReleases,
  makeReleaseLive,
  publishRelease,
} from "../api/portfolio";

export const draftQueryOptions = queryOptions({
  queryKey: ["portfolio", "draft"],
  queryFn: ({ signal }) => fetchDraft(signal),
});

export const releasesQueryOptions = queryOptions({
  queryKey: ["portfolio", "releases"],
  queryFn: ({ signal }) => fetchReleases(signal),
});

export const publishMutationOptions = mutationOptions({
  mutationFn: publishRelease,
  onSettled: (_release, _error, _variables, _result, { client }) =>
    client.invalidateQueries({ queryKey: ["portfolio"] }),
});

export const makeLiveMutationOptions = mutationOptions({
  mutationFn: makeReleaseLive,
  onSettled: (_release, _error, _id, _result, { client }) =>
    client.invalidateQueries({ queryKey: ["portfolio"] }),
});
