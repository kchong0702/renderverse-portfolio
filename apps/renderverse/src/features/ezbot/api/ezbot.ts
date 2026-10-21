import { CONFIG } from "@/app/config";

const CHAT_URL = `${CONFIG.ezbotApiUrl}/ezbot/v1/chat`;
const HEALTH_URL = `${CONFIG.ezbotApiUrl}/health`;

// Mirrors ezbot's chat limits (apps/ezbot/config.toml)
export const MAX_MESSAGE_CHARS = 2000;
export const MAX_HISTORY = 20;

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatHistoryMessage[];
}

export type ChatStreamEvent =
  | { event: "token"; data: { content: string } }
  | { event: "done"; data: { finish_reason: "stop" } }
  | {
      event: "error";
      data: { status_code: number; code: string; message: string };
    };

export async function fetchHealth(signal?: AbortSignal) {
  const response = await fetch(HEALTH_URL, { signal });
  if (!response.ok) {
    throw new Error(`Ezbot health check failed with status ${response.status}`);
  }
  return true;
}

// Parse one SSE block into { event, data }, skipping keep-alive comments
function parseEvent(block: string): ChatStreamEvent | null {
  let event = "message";
  const data: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue;

    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    const value =
      separator === -1 ? "" : line.slice(separator + 1).replace(/^ /, "");

    if (field === "event") event = value;
    if (field === "data") data.push(value);
  }

  return data.length
    ? ({ event, data: JSON.parse(data.join("\n")) } as ChatStreamEvent)
    : null;
}

/**
 * POST a chat message to ezbot and yield its SSE events ({ event, data }) as
 * they arrive: `token` chunks, then `done` or `error`.
 *
 * Abort `signal` to cancel; ezbot stops generating once the request drops.
 */
export async function* streamChat(
  { message, history }: ChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(CHAT_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ message, history }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Ezbot request failed with status ${response.status}`);
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) return;

      buffer += value;

      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const event = parseEvent(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (event) yield event;
      }
    }
  } finally {
    // Closes the connection when the consumer stops early
    reader.cancel().catch(() => {});
  }
}
