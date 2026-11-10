import { http } from "@/shared/api/http";

export interface Profile {
  name: string;
  headline: string;
}

export const fetchProfile = (signal?: AbortSignal) =>
  http.get<Profile>("/ops-api/v1/profile", signal);
