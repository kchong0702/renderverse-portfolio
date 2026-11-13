import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

export type WorkMode = "onsite" | "hybrid" | "remote";
export type SalaryPeriod = "hour" | "month" | "year";

export interface Salary {
  amount: number;
  currency: string;
  period: SalaryPeriod;
}

export interface Preferences {
  target_roles: string;
  location: string;
  countries: string[];
  visa_free_countries: string[];
  work_modes: WorkMode[];
  min_salary: Salary | null;
  min_score: number;
  run_at: string;
}

export type PreferencesPatch = Partial<Preferences>;

const URL = `${config.opsApiUrl}/preferences`;

export const fetchPreferences = (signal?: AbortSignal) =>
  http.get<Preferences>(URL, signal);

export const updatePreferences = (patch: PreferencesPatch) =>
  http.patch<Preferences>(URL, patch);
