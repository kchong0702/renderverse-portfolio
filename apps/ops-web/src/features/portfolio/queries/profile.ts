import { queryOptions } from "@tanstack/react-query";
import { fetchProfile } from "../api/profile";

export const profileQueryOptions = queryOptions({
  queryKey: ["profile"],
  queryFn: ({ signal }) => fetchProfile(signal),
});
