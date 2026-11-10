import i18n from "@/i18n";
import { ApiError, http, stream } from "@/shared/api/http";

export type DocumentKind = "resume" | "cv" | "cover_letter";

export interface DocumentSummary {
  id: string;
  kind: DocumentKind;
  title: string;
  master: boolean;
  updated_at: string;
}

export interface Widget {
  label: string | null;
  input_value: string | null;
  input_placeholder: string | null;
  submit_btn: string | null;
  cancel_btn: string | null;
  choose: "document" | null;
  kind: DocumentKind | null;
}

export interface Answer {
  input?: string;
  accept?: boolean;
}

export interface Step {
  id: string;
  parent: string | null;
  name: string;
  status: "running" | "done" | "failed" | "waiting";
}

export type Outcome =
  | { status: "completed"; reply: string }
  | { status: "input_required"; task_id: string; widget: Widget }
  | { status: "failed"; reason: string }
  | { status: "cancelled" };

export interface Changeset {
  document_id: string;
  title: string;
  changeset_id: string;
  edits: number;
}

export type RunEvent =
  | { status: "started"; task_id: string }
  | { status: "thinking"; turn: string; text: string }
  | { status: "text"; turn: string; text: string }
  | { status: "step"; step: Step }
  | ({ status: "changeset" } & Changeset)
  | Outcome;

export interface Chat {
  kind: "assistant" | "document";
  id: string;
}

export interface ChatMessage {
  chat: Chat;
  text: string;
}

export interface TaskAnswer {
  chat: Chat;
  taskId: string;
  answer: Answer;
  shown: string;
}

export interface TurnCursor {
  chat: Chat;
  lastEventId: string;
}

export interface Task {
  chat: Chat;
  taskId: string;
}

type OnEvent = (event: RunEvent, id: string | undefined) => void;

type OnReconnect = (attempt: number) => void;

const URL = "/ops-api/v1";

export const MAX_RECONNECTS = 5;

const DEFAULT_RETRY_MS = 2000;

const MAX_RETRY_MS = 15_000;

const TERMINAL: ReadonlySet<RunEvent["status"]> = new Set([
  "completed",
  "input_required",
  "failed",
  "cancelled",
]);

const chatUrl = ({ kind, id }: Chat) =>
  kind === "document"
    ? `${URL}/documents/${id}/chat`
    : `${URL}/assistant/chats/${id}`;

const taskUrl = ({ chat, taskId }: Task) =>
  `${chatUrl(chat)}/tasks/${encodeURIComponent(taskId)}`;

const openChatStream = (
  chat: Chat,
  lastEventId: string | null,
  signal: AbortSignal,
  onRetry: (ms: number) => void,
) =>
  stream(
    `${chatUrl(chat)}/stream`,
    {
      headers: lastEventId ? { "Last-Event-ID": lastEventId } : undefined,
      signal,
    },
    onRetry,
  );

const wait = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason);
      },
      { once: true },
    );
  });

async function streamTurn(
  chat: Chat,
  request: { url: string; body: unknown } | null,
  lastEventId: string | null,
  signal: AbortSignal,
  onEvent: OnEvent,
  onReconnect: OnReconnect,
): Promise<void> {
  let retryMs = DEFAULT_RETRY_MS;
  let reconnects = 0;
  const onRetry = (ms: number) => {
    retryMs = ms;
  };

  let reader: Awaited<ReturnType<typeof stream>> | null = request
    ? await stream(
        request.url,
        { method: "POST", body: JSON.stringify(request.body), signal },
        onRetry,
      )
    : await openChatStream(chat, lastEventId, signal, onRetry);
  for (;;) {
    if (reader) {
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          const event = JSON.parse(value.data) as RunEvent;
          lastEventId = value.id ?? lastEventId;
          reconnects = 0;
          onEvent(event, value.id);
          if (TERMINAL.has(event.status)) return;
        }
      } catch (error) {
        if (signal.aborted) throw error;
      }
    }

    if (++reconnects > MAX_RECONNECTS)
      throw new Error(i18n.t("assistant.connectionLost"));
    onReconnect(reconnects);
    await wait(Math.min(retryMs * 2 ** (reconnects - 1), MAX_RETRY_MS), signal);
    reader = await openChatStream(chat, lastEventId, signal, onRetry).catch(
      (error: unknown) => {
        if (signal.aborted || error instanceof ApiError) throw error;
        return null;
      },
    );
  }
}

export const sendMessage = (
  { chat, text }: ChatMessage,
  signal: AbortSignal,
  onEvent: OnEvent,
  onReconnect: OnReconnect,
) =>
  streamTurn(
    chat,
    {
      url: `${chatUrl(chat)}/messages`,
      body: { text },
    },
    null,
    signal,
    onEvent,
    onReconnect,
  );

export const answerTask = (
  { answer, ...task }: TaskAnswer,
  signal: AbortSignal,
  onEvent: OnEvent,
  onReconnect: OnReconnect,
) =>
  streamTurn(
    task.chat,
    { url: `${taskUrl(task)}/answer`, body: answer },
    null,
    signal,
    onEvent,
    onReconnect,
  );

export const resumeTurn = (
  { chat, lastEventId }: TurnCursor,
  signal: AbortSignal,
  onEvent: OnEvent,
  onReconnect: OnReconnect,
) => streamTurn(chat, null, lastEventId, signal, onEvent, onReconnect);

export const cancelTask = (task: Task) =>
  http.post<void>(`${taskUrl(task)}/cancel`);

export const fetchDocuments = (signal?: AbortSignal) =>
  http.get<DocumentSummary[]>(`${URL}/documents`, signal);
