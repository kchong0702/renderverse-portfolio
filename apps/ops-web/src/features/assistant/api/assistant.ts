import i18n from "@/i18n";
import { ApiError, http, stream } from "@/shared/api/http";

export type DocumentKind = "resume" | "cv" | "cover_letter";

export interface DocumentSummary {
  id: string;
  kind: DocumentKind;
  title: string;
  master: boolean;
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

export type RunEvent =
  | { status: "started"; task_id: string }
  | { status: "thinking"; turn: string; text: string }
  | { status: "text"; turn: string; text: string }
  | { status: "step"; step: Step }
  | Outcome;

export interface ChatMessage {
  chatId: string;
  text: string;
}

export interface TaskAnswer {
  chatId: string;
  taskId: string;
  answer: Answer;
  shown: string;
}

export interface TurnCursor {
  chatId: string;
  lastEventId: string;
}

export interface Task {
  chatId: string;
  taskId: string;
}

type OnEvent = (event: RunEvent, id: string | undefined) => void;

const URL = "/ops-api/v1/assistant";

const MAX_RECONNECTS = 5;

const DEFAULT_RETRY_MS = 2000;

const MAX_RETRY_MS = 15_000;

const TERMINAL: ReadonlySet<RunEvent["status"]> = new Set([
  "completed",
  "input_required",
  "failed",
  "cancelled",
]);

const taskUrl = ({ chatId, taskId }: Task) =>
  `${URL}/chats/${chatId}/tasks/${encodeURIComponent(taskId)}`;

const openChatStream = (
  chatId: string,
  lastEventId: string | null,
  signal: AbortSignal,
  onRetry: (ms: number) => void,
) =>
  stream(
    `${URL}/chats/${chatId}/stream`,
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
  chatId: string,
  request: { url: string; body: unknown } | null,
  lastEventId: string | null,
  signal: AbortSignal,
  onEvent: OnEvent,
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
    : await openChatStream(chatId, lastEventId, signal, onRetry);
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
    await wait(Math.min(retryMs * 2 ** (reconnects - 1), MAX_RETRY_MS), signal);
    reader = await openChatStream(chatId, lastEventId, signal, onRetry).catch(
      (error: unknown) => {
        if (signal.aborted || error instanceof ApiError) throw error;
        return null;
      },
    );
  }
}

export const sendMessage = (
  { chatId, ...message }: ChatMessage,
  signal: AbortSignal,
  onEvent: OnEvent,
) =>
  streamTurn(
    chatId,
    { url: `${URL}/chats/${chatId}/messages`, body: message },
    null,
    signal,
    onEvent,
  );

export const answerTask = (
  { answer, ...task }: TaskAnswer,
  signal: AbortSignal,
  onEvent: OnEvent,
) =>
  streamTurn(
    task.chatId,
    { url: `${taskUrl(task)}/answer`, body: answer },
    null,
    signal,
    onEvent,
  );

export const resumeTurn = (
  { chatId, lastEventId }: TurnCursor,
  signal: AbortSignal,
  onEvent: OnEvent,
) => streamTurn(chatId, null, lastEventId, signal, onEvent);

export const cancelTask = (task: Task) =>
  http.post<void>(`${taskUrl(task)}/cancel`);

export const fetchDocuments = (signal?: AbortSignal) =>
  http.get<DocumentSummary[]>("/ops-api/v1/documents", signal);
