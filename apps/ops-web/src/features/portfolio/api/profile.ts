import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

export interface Profile {
  name: string;
  headline: string;
}

export const fetchProfile = (signal?: AbortSignal) =>
  http.get<Profile>(`${config.opsApiUrl}/profile`, signal);
