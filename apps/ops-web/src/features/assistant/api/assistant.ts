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
  text: string;
  document_id?: string;
}

export interface TaskAnswer {
  taskId: string;
  answer: Answer;
  shown: string;
}

const URL = "/ops-api/v1/assistant";

export const sendMessage = (message: ChatMessage) =>
  http.post<AssistantReply>(`${URL}/messages`, message);

export const answerTask = ({ taskId, answer }: TaskAnswer) =>
  http.post<AssistantReply>(
    `${URL}/tasks/${encodeURIComponent(taskId)}/answer`,
    answer,
  );
