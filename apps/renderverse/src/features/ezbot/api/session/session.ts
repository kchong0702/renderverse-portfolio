import { request } from "../client";
import { toApiError } from "../errors";
import { setSessionId } from "./state";
import { SESSION_PATH } from "./constants";
import type { EzbotSession } from "./types";

export async function createSession(
  signal?: AbortSignal,
): Promise<EzbotSession> {
  const response = await request(SESSION_PATH, { method: "POST", signal });
  if (!response.ok) throw await toApiError(response);
  const session: EzbotSession = await response.json();
  setSessionId(session.session_id);
  return session;
}
