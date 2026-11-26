import i18n from "@/i18n";
import { ApiError, http, stream } from "@/shared/api/http";
import type { FieldValue, ImportedEntry } from "@/features/data/api/data";
import { config } from "@/shared/config";

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
  detail: string | null;
  document_id: string | null;
}

export type ProfileEdit =
  | {
      kind: "about";
      field: "name" | "headline" | "location" | "email" | "phone" | "summary";
      value: string;
    }
  | {
      kind: "entry";
      fact: string;
      field: Exclude<keyof ImportedEntry, "kind">;
      value: FieldValue;
    }
  | { kind: "new_entry"; entry: ImportedEntry }
  | { kind: "new_skill"; name: string; group: string }
  | { kind: "new_link"; label: string; url: string };

export interface ApprovalRow {
  edit: ProfileEdit;
  entry: string | null;
  current: FieldValue;
}

export type Outcome =
  | { status: "completed"; reply: string }
  | { status: "input_required"; task_id: string; widget: Widget }
  | {
      status: "profile_approval";
      task_id: string;
      source: string;
      rows: ApprovalRow[];
    }
  | { status: "failed"; reason: string }
  | { status: "cancelled" };

export interface ChangesetRecord {
  id: string;
  changeset: { edits: unknown[]; status: "pending" | "accepted" | "rejected" };
}

export type RunEvent =
  | { status: "started"; task_id: string }
  | { status: "thinking"; turn: string; text: string }
  | { status: "text"; turn: string; text: string }
  | { status: "step"; step: Step }
  | {
      status: "changeset";
      document_id: string;
      changeset_id: string;
      created_at: string;
    }
  | { status: "profile_saved"; saved: number }
  | { status: "reconnecting"; attempt: number; retry_at: string }
  | { status: "reconnected" }
  | Outcome;

export type Agent = "career-director" | "career-consultant";

export type Conversation =
  | { agent: "career-director" }
  | { agent: "career-consultant"; documentId: string };

export interface AgentSession {
  agent: Agent;
  thread_id: string;
}

export interface ThreadMessage {
  id: string;
  role: "user" | "agent";
  text: string;
  created_at: string;
  document_id: string | null;
  agent: string | null;
  changesets: { id: string; document_id: string; created_at: string }[];
  steps: Step[] | null;
  failure: string | null;
}

export interface ThreadPage {
  messages: ThreadMessage[];
  has_more: boolean;
}

export interface Chat {
  threadId: string;
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

export interface TaskDecision {
  chat: Chat;
  taskId: string;
  decision: { approve: boolean; message?: string };
}

export interface Task {
  chat: Chat;
  taskId: string;
}

type OnEvent = (event: RunEvent) => void;

type OnReconnect = (attempt: number) => void;

const URL = config.opsApiUrl;

export const MAX_RECONNECTS = 5;

const DEFAULT_RETRY_MS = 2000;

const MAX_RETRY_MS = 15_000;

const TERMINAL: ReadonlySet<RunEvent["status"]> = new Set([
  "completed",
  "input_required",
  "profile_approval",
  "failed",
  "cancelled",
]);

const threadUrl = ({ threadId }: Pick<Chat, "threadId">) =>
  `${URL}/agent/threads/${encodeURIComponent(threadId)}`;

const taskUrl = ({ chat, taskId }: Task) =>
  `${threadUrl(chat)}/tasks/${encodeURIComponent(taskId)}`;

const openChatStream = (
  chat: Chat,
  lastEventId: string | null,
  signal: AbortSignal,
  onRetry: (ms: number) => void,
) =>
  stream(
    `${threadUrl(chat)}/stream`,
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
  signal: AbortSignal,
  onEvent: OnEvent,
  onReconnect: OnReconnect,
): Promise<void> {
  let retryMs = DEFAULT_RETRY_MS;
  let reconnects = 0;
  let lastEventId: string | null = null;
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
          onEvent(event);
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
      url: `${threadUrl(chat)}/messages`,
      body: { text },
    },
    signal,
    onEvent,
    onReconnect,
  );

export const sendRefused = (error: Error | null): error is ApiError =>
  error instanceof ApiError && error.status === 409;

export const answerTask = (
  { answer, ...task }: TaskAnswer,
  signal: AbortSignal,
  onEvent: OnEvent,
  onReconnect: OnReconnect,
) =>
  streamTurn(
    task.chat,
    { url: `${taskUrl(task)}/answer`, body: answer },
    signal,
    onEvent,
    onReconnect,
  );

export const decideTask = (
  { decision, ...task }: TaskDecision,
  signal: AbortSignal,
  onEvent: OnEvent,
  onReconnect: OnReconnect,
) =>
  streamTurn(
    task.chat,
    { url: `${taskUrl(task)}/decision`, body: decision },
    signal,
    onEvent,
    onReconnect,
  );

export const followTurn = (
  chat: Chat,
  signal: AbortSignal,
  onEvent: OnEvent,
  onReconnect: OnReconnect,
) => streamTurn(chat, null, signal, onEvent, onReconnect);

export const cancelTask = (task: Task) => http.delete(taskUrl(task));

const sessionQuery = (conversation: Conversation) =>
  conversation.agent === "career-consultant"
    ? `?${new URLSearchParams({ document_id: conversation.documentId })}`
    : "";

export const fetchSession = (
  conversation: Conversation,
  signal?: AbortSignal,
) =>
  http.get<AgentSession>(
    `${URL}/agent/sessions/${conversation.agent}${sessionQuery(conversation)}`,
    signal,
  );

export const startThread = (conversation: Conversation) =>
  http.post<AgentSession>(
    `${URL}/agent/sessions/${conversation.agent}/threads${sessionQuery(conversation)}`,
  );

export const fetchThreadMessages = (
  {
    threadId,
    before,
  }: Pick<Chat, "threadId"> & {
    before: string | null;
  },
  signal: AbortSignal,
) =>
  http.get<ThreadPage>(
    `${threadUrl({ threadId })}/messages?${new URLSearchParams({
      limit: "30",
      ...(before && { before }),
    })}`,
    signal,
  );

export const fetchDocuments = (signal?: AbortSignal) =>
  http.get<DocumentSummary[]>(`${URL}/documents`, signal);

export const fetchChangesets = (documentId: string, signal?: AbortSignal) =>
  http.get<ChangesetRecord[]>(
    `${URL}/documents/${encodeURIComponent(documentId)}/changesets`,
    signal,
  );
