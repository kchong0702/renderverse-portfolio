import { wait } from "@/shared/lib/utility";
import { request } from "../client";
import { toApiError } from "../errors";
import {
  CHAT_PATH,
  CHAT_STREAM_PATH,
  DEFAULT_RETRY_MS,
  TERMINAL_EVENT_TYPES,
  MAX_RECONNECTS,
  MAX_RETRY_MS,
} from "./constants";
import { readEvents } from "./sse";
import type { ChatStreamEvent } from "./types";

export async function* streamChat(
  message: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  let lastEventId: string | null = null;
  let retryMs = DEFAULT_RETRY_MS;
  let reconnects = 0;

  let response: Response | null = await request(CHAT_PATH, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ message }),
    signal,
  });

  while (true) {
    if (response) {
      if (!response.ok) throw await toApiError(response);
      try {
        for await (const parsed of readEvents(response)) {
          if (parsed.id) lastEventId = parsed.id;
          if (parsed.retry) retryMs = parsed.retry;
          if (!parsed.event) continue;
          reconnects = 0;
          yield parsed.event;
          if (TERMINAL_EVENT_TYPES.has(parsed.event.type)) return;
        }
      } catch (error) {
        if (signal?.aborted) throw error;
      }
    }

    if (++reconnects > MAX_RECONNECTS) {
      throw new Error("Lost the connection to Ezbot");
    }
    await wait(Math.min(retryMs * 2 ** (reconnects - 1), MAX_RETRY_MS), signal);
    try {
      response = await request(CHAT_STREAM_PATH, {
        headers: {
          Accept: "text/event-stream",
          ...(lastEventId ? { "Last-Event-ID": lastEventId } : {}),
        },
        signal,
      });
    } catch (error) {
      if (signal?.aborted) throw error;
      response = null;
    }
  }
}
