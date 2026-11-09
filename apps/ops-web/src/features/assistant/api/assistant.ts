import { http } from "@/shared/api/http";

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

export type AssistantReply =
  | { status: "completed"; reply: string }
  | { status: "input_required"; task_id: string; widget: Widget }
  | { status: "failed"; reason: string };

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

const URL = "/ops-api/v1/assistant";

export const sendMessage = ({ chatId, ...message }: ChatMessage) =>
  http.post<AssistantReply>(`${URL}/chats/${chatId}/messages`, message);

export const answerTask = ({ chatId, taskId, answer }: TaskAnswer) =>
  http.post<AssistantReply>(
    `${URL}/chats/${chatId}/tasks/${encodeURIComponent(taskId)}/answer`,
    answer,
  );
