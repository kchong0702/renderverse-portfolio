import { http } from "@/shared/api/http";

const base = "/ops-api/v1";

export interface Me {
  id: string;
  email: string;
}

export interface SignInMethods {
  /** False while ops-api runs with auth disabled */
  required: boolean;
  password: boolean;
  google: boolean;
  github: boolean;
}

export type OAuthProvider = "google" | "github";

export interface PasswordSignIn {
  email: string;
  password: string;
}

export const fetchMe = (signal?: AbortSignal) =>
  http.get<Me>(`${base}/me`, signal);

export const fetchSignInMethods = (signal?: AbortSignal) =>
  http.get<SignInMethods>(`${base}/auth/methods`, signal);

export const signInWithPassword = (body: PasswordSignIn) =>
  http.post<void>(`${base}/auth/password`, body);

export const signOut = () => http.post<void>(`${base}/auth/sign-out`);

/** A full-page navigation: ops-api redirects to the provider and back */
export const oauthLoginUrl = (provider: OAuthProvider, next: string) =>
  `${base}/auth/${provider}/login?${new URLSearchParams({ next })}`;
