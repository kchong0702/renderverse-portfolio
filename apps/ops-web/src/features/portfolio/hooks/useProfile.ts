import { useMutation, useQuery } from "@tanstack/react-query";
import {
  addEntryMutationOptions,
  addSkillMutationOptions,
  deleteEntryMutationOptions,
  deleteSkillMutationOptions,
  entriesQueryOptions,
  profileQueryOptions,
  saveEntryMutationOptions,
  saveSkillMutationOptions,
  skillsQueryOptions,
  updateProfileMutationOptions,
} from "../queries/profile";

export function useProfile() {
  return useQuery(profileQueryOptions);
}

export function useUpdateProfile() {
  return useMutation(updateProfileMutationOptions);
}

export function useEntries() {
  return useQuery(entriesQueryOptions);
}

export function useAddEntry() {
  return useMutation(addEntryMutationOptions);
}

export function useSaveEntry() {
  return useMutation(saveEntryMutationOptions);
}

export function useDeleteEntry() {
  return useMutation(deleteEntryMutationOptions);
}

export function useSkills() {
  return useQuery(skillsQueryOptions);
}

export function useAddSkill() {
  return useMutation(addSkillMutationOptions);
}

export function useSaveSkill() {
  return useMutation(saveSkillMutationOptions);
}

export function useDeleteSkill() {
  return useMutation(deleteSkillMutationOptions);
}
