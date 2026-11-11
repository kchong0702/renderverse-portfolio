import { useQuery } from "@tanstack/react-query";
import { profileQueryOptions } from "../queries/profile";

export function useProfile() {
  return useQuery(profileQueryOptions);
}
