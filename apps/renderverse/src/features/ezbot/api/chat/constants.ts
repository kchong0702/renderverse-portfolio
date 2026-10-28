import type { ChatStreamEventType } from "./types";

export const CHAT_PATH = "/chat";

export const CHAT_STREAM_PATH = "/chat/stream";

export const CHAT_STOP_PATH = "/chat/stop";

export const MAX_MESSAGE_CHARS = 2000;

export const MAX_RECONNECTS = 5;

export const DEFAULT_RETRY_MS = 2000;

export const MAX_RETRY_MS = 15_000;

export const TERMINAL_EVENT_TYPES: ReadonlySet<ChatStreamEventType> = new Set([
  "response.completed",
  "response.cancelled",
  "response.failed",
]);
