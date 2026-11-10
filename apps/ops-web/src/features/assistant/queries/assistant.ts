import { mutationOptions, queryOptions } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/http";
import {
  answerTask,
  cancelTask,
  fetchDocuments,
  resumeTurn,
  sendMessage,
  type ChatMessage,
  type Task,
  type TaskAnswer,
  type TurnCursor,
} from "../api/assistant";
import { useAssistantStore } from "../state/assistantStore";

const { add, apply, restore } = useAssistantStore.getState();

let streamController = new AbortController();

const newStreamSignal = () => {
  streamController = new AbortController();
  return streamController.signal;
};

const startTurn = () => {
  add({
    role: "assistant",
    taskId: null,
    lastEventId: null,
    parts: [],
    outcome: null,
  });
  return newStreamSignal();
};

const failTurn = (error: Error) =>
  apply({ status: "failed", reason: error.message });

export const sendMessageMutationOptions = mutationOptions({
  mutationKey: ["assistant", "send"],
  mutationFn: (message: ChatMessage) =>
    sendMessage(message, startTurn(), apply),
  onMutate: ({ text }) => add({ role: "user", text }),
  onError: failTurn,
});

export const answerTaskMutationOptions = mutationOptions({
  mutationKey: ["assistant", "answer"],
  mutationFn: (answer: TaskAnswer) => answerTask(answer, startTurn(), apply),
  onMutate: ({ shown }) => {
    const previous = useAssistantStore.getState().entries;
    add({ role: "user", text: shown });
    return { previous };
  },
  onError: (error, _answer, result) =>
    error instanceof ApiError && result
      ? restore(result.previous)
      : failTurn(error),
});

export const resumeTurnMutationOptions = mutationOptions({
  mutationKey: ["assistant", "resume"],
  mutationFn: (turn: TurnCursor) => resumeTurn(turn, newStreamSignal(), apply),
  onError: (error) =>
    error instanceof ApiError && error.status === 404
      ? apply({ status: "cancelled" })
      : failTurn(error),
});

export const stopMutationOptions = mutationOptions({
  mutationKey: ["assistant", "stop"],
  mutationFn: (task: Task) => cancelTask(task),
  onSuccess: () => {
    apply({ status: "cancelled" });
    streamController.abort();
  },
});

export const documentsQueryOptions = queryOptions({
  queryKey: ["documents"],
  queryFn: ({ signal }) => fetchDocuments(signal),
});
