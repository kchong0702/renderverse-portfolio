import {
  mutationOptions,
  queryOptions,
  type QueryClient,
  type QueryKey,
} from "@tanstack/react-query";
import {
  addEntry,
  addSkill,
  deleteEntry,
  deleteSkill,
  fetchEntries,
  fetchProfile,
  fetchSkills,
  saveEntry,
  saveSkill,
  updateProfile,
  type Entry,
  type ProfilePatch,
  type Skill,
} from "../api/profile";

const updateProfileKey = ["profile", "update"] as const;

export const profileQueryOptions = queryOptions({
  queryKey: ["profile"],
  queryFn: ({ signal }) => fetchProfile(signal),
});

export const entriesQueryOptions = queryOptions({
  queryKey: ["profile", "entries"],
  queryFn: ({ signal }) => fetchEntries(signal),
});

export const skillsQueryOptions = queryOptions({
  queryKey: ["profile", "skills"],
  queryFn: ({ signal }) => fetchSkills(signal),
});

async function changeList<T extends { id: string }>(
  client: QueryClient,
  queryKey: QueryKey,
  change: (items: T[]) => T[],
) {
  await client.cancelQueries({ queryKey });
  const previous = client.getQueryData<T[]>(queryKey);
  if (previous) client.setQueryData(queryKey, change(previous));
  return { previous };
}

export const updateProfileMutationOptions = mutationOptions({
  mutationKey: updateProfileKey,
  mutationFn: updateProfile,
  onMutate: async (patch: ProfilePatch, { client }) => {
    const { queryKey } = profileQueryOptions;
    await client.cancelQueries({ queryKey });
    const previous = client.getQueryData(queryKey);
    if (previous) client.setQueryData(queryKey, { ...previous, ...patch });
    return { previous };
  },
  onError: (_error, _patch, result, { client }) => {
    if (result?.previous)
      client.setQueryData(profileQueryOptions.queryKey, result.previous);
  },
  onSuccess: (profile, _patch, _result, { client }) => {
    if (client.isMutating({ mutationKey: updateProfileKey }) === 1)
      client.setQueryData(profileQueryOptions.queryKey, profile);
  },
});

export const addEntryMutationOptions = mutationOptions({
  mutationFn: addEntry,
  onSettled: (_entry, _error, _create, _result, { client }) =>
    client.invalidateQueries({ queryKey: entriesQueryOptions.queryKey }),
});

export const saveEntryMutationOptions = mutationOptions({
  mutationFn: saveEntry,
  onMutate: (entry: Entry, { client }) =>
    changeList<Entry>(client, entriesQueryOptions.queryKey, (entries) =>
      entries.map((e) => (e.id === entry.id ? entry : e)),
    ),
  onError: (_error, _entry, result, { client }) => {
    if (result?.previous)
      client.setQueryData(entriesQueryOptions.queryKey, result.previous);
  },
  onSettled: (_saved, _error, _entry, _result, { client }) =>
    client.invalidateQueries({ queryKey: entriesQueryOptions.queryKey }),
});

export const deleteEntryMutationOptions = mutationOptions({
  mutationFn: deleteEntry,
  onMutate: (id: string, { client }) =>
    changeList<Entry>(client, entriesQueryOptions.queryKey, (entries) =>
      entries.filter((e) => e.id !== id),
    ),
  onError: (_error, _id, result, { client }) => {
    if (result?.previous)
      client.setQueryData(entriesQueryOptions.queryKey, result.previous);
  },
});

export const addSkillMutationOptions = mutationOptions({
  mutationFn: addSkill,
  onSettled: (_skill, _error, _write, _result, { client }) =>
    client.invalidateQueries({ queryKey: skillsQueryOptions.queryKey }),
});

export const saveSkillMutationOptions = mutationOptions({
  mutationFn: saveSkill,
  onMutate: (skill: Skill, { client }) =>
    changeList<Skill>(client, skillsQueryOptions.queryKey, (skills) =>
      skills.map((s) => (s.id === skill.id ? skill : s)),
    ),
  onError: (_error, _skill, result, { client }) => {
    if (result?.previous)
      client.setQueryData(skillsQueryOptions.queryKey, result.previous);
  },
  onSettled: (_saved, _error, _skill, _result, { client }) =>
    client.invalidateQueries({ queryKey: skillsQueryOptions.queryKey }),
});

export const deleteSkillMutationOptions = mutationOptions({
  mutationFn: deleteSkill,
  onMutate: (id: string, { client }) =>
    changeList<Skill>(client, skillsQueryOptions.queryKey, (skills) =>
      skills.filter((s) => s.id !== id),
    ),
  onError: (_error, _id, result, { client }) => {
    if (result?.previous)
      client.setQueryData(skillsQueryOptions.queryKey, result.previous);
  },
});
