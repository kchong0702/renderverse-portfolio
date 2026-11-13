import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

export type EntryKind = "role" | "education" | "project";
export type YearMonth = `${number}-${number}`;

export interface ProfileLink {
  label: string;
  url: string;
}

export interface Profile {
  name: string;
  headline: string;
  location: string;
  email: string;
  phone: string;
  links: ProfileLink[];
  summary: string;
}

export type ProfilePatch = Partial<Profile>;

export interface EntryWrite {
  title: string;
  organisation: string;
  location: string;
  start: YearMonth | null;
  end: YearMonth | "present" | null;
  summary: string;
  highlights: string[];
  link: string | null;
  code_link: string | null;
  tools: string[];
  archived: boolean;
  on_site: boolean;
}

export interface EntryCreate extends EntryWrite {
  kind: EntryKind;
}

export interface Entry extends EntryCreate {
  id: string;
  image_id: string | null;
  video_id: string | null;
}

export interface SkillWrite {
  name: string;
  group: string;
  archived: boolean;
}

export interface Skill extends SkillWrite {
  id: string;
}

const URL = `${config.opsApiUrl}/profile`;

export const fetchProfile = (signal?: AbortSignal) =>
  http.get<Profile>(URL, signal);

export const updateProfile = (patch: ProfilePatch) =>
  http.patch<Profile>(URL, patch);

export const fetchEntries = (signal?: AbortSignal) =>
  http.get<Entry[]>(`${URL}/entries`, signal);

export const addEntry = (entry: EntryCreate) =>
  http.post<Entry>(`${URL}/entries`, entry);

export const saveEntry = ({ id, ...entry }: Entry) =>
  http.put<Entry>(`${URL}/entries/${id}`, entry);

export const deleteEntry = (id: string) => http.delete(`${URL}/entries/${id}`);

export const fetchSkills = (signal?: AbortSignal) =>
  http.get<Skill[]>(`${URL}/skills`, signal);

export const addSkill = (skill: SkillWrite) =>
  http.post<Skill>(`${URL}/skills`, skill);

export const saveSkill = ({ id, ...skill }: Skill) =>
  http.put<Skill>(`${URL}/skills/${id}`, skill);

export const deleteSkill = (id: string) => http.delete(`${URL}/skills/${id}`);
