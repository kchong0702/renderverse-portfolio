import { http, stream } from "@/shared/api/http";

export interface Widget {
  label: string | null;
  input_value: string | null;
  input_placeholder: string | null;
  submit_btn: string | null;
  cancel_btn: string | null;
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
  document_id?: string;
}

export interface TaskAnswer {
  chatId: string;
  taskId: string;
  answer: Answer;
  shown: string;
}

export interface Task {
  chatId: string;
  taskId: string;
}

type OnEvent = (event: RunEvent) => void;

const URL = "/ops-api/v1/assistant";

const taskUrl = ({ chatId, taskId }: Task) =>
  `${URL}/chats/${chatId}/tasks/${encodeURIComponent(taskId)}`;

export const sendMessage = (
  { chatId, ...message }: ChatMessage,
  signal: AbortSignal,
  onEvent: OnEvent,
) => stream(`${URL}/chats/${chatId}/messages`, message, signal, onEvent);

export const answerTask = (
  { answer, ...task }: TaskAnswer,
  signal: AbortSignal,
  onEvent: OnEvent,
) => stream(`${taskUrl(task)}/answer`, answer, signal, onEvent);

export const cancelTask = (task: Task) =>
  http.post<void>(`${taskUrl(task)}/cancel`);
