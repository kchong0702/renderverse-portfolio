import { API_URL } from "./constants";
import { SESSION_ID_HEADER } from "./session/constants";
import { getSessionId } from "./session/state";

export function request(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const sessionId = getSessionId();
  if (sessionId) headers.set(SESSION_ID_HEADER, sessionId);
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
}
