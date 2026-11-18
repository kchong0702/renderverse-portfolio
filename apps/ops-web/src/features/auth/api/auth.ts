import { http } from "@/shared/api/http";
import { config } from "@/shared/config";

const base = config.opsApiUrl;

export interface Me {
  id: string;
  email: string;
  role: "admin" | "user";
}

export interface OAuthProvider {
  name: string;
  label: string;
}

export interface SignInMethods {
  required: boolean;
  password: boolean;
  providers: OAuthProvider[];
}

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

export const oauthLoginUrl = (provider: string, next: string) =>
  `${base}/auth/${provider}/login?${new URLSearchParams({ next })}`;
