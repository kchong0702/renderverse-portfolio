import {
  MutationObserver,
  mutationOptions,
  queryOptions,
} from "@tanstack/react-query";
import i18n from "@/i18n";
import { ApiError } from "@/shared/api/http";
import { queryClient } from "@/shared/api/queryClient";
import {
  answerTask,
  cancelTask,
  fetchDocuments,
  resumeTurn,
  sendMessage,
  type ChatMessage,
  type TaskAnswer,
} from "../api/assistant";
import { useAssistantStore } from "../state/assistantStore";

const { add, apply, restore } = useAssistantStore.getState();

let run = new AbortController();

const follow = () => {
  run = new AbortController();
  return run.signal;
};

const start = () => {
  add({
    role: "assistant",
    taskId: null,
    lastEventId: null,
    parts: [],
    outcome: null,
  });
  return follow();
};

const settle = (_data: unknown, error: Error | null) =>
  apply({
    status: "failed",
    reason: error?.message ?? i18n.t("assistant.interrupted"),
  });

export const sendMessageMutationOptions = mutationOptions({
  mutationKey: ["assistant", "send"],
  mutationFn: (message: ChatMessage) => sendMessage(message, start(), apply),
  onMutate: ({ text }) => add({ role: "user", text }),
  onSettled: settle,
});

export const answerTaskMutationOptions = mutationOptions({
  mutationKey: ["assistant", "answer"],
  mutationFn: (answer: TaskAnswer) => answerTask(answer, start(), apply),
  onMutate: ({ shown }) => {
    const previous = useAssistantStore.getState().entries;
    add({ role: "user", text: shown });
    return { previous };
  },
  onError: (error, _answer, result) => {
    if (error instanceof ApiError && result) restore(result.previous);
  },
  onSettled: settle,
});

const resumeMutationOptions = mutationOptions({
  mutationKey: ["assistant", "resume"],
  mutationFn: (turn: { chatId: string; lastEventId: string }) =>
    resumeTurn(turn, follow(), apply),
  onSettled: (data, error) =>
    error instanceof ApiError && error.status === 404
      ? apply({ status: "cancelled" })
      : settle(data, error),
});

const { chatId, entries } = useAssistantStore.getState();
const pending = entries.at(-1);
if (pending?.role === "assistant" && !pending.outcome && pending.lastEventId)
  new MutationObserver(queryClient, resumeMutationOptions)
    .mutate({ chatId, lastEventId: pending.lastEventId })
    .catch(() => {});

export const stopMutationOptions = mutationOptions({
  mutationKey: ["assistant", "stop"],
  mutationFn: async ({
    chatId,
    taskId,
  }: {
    chatId: string;
    taskId: string | null;
  }) => {
    if (taskId) await cancelTask({ chatId, taskId });
  },
  onSettled: () => {
    apply({ status: "cancelled" });
    run.abort();
  },
});

export const documentsQueryOptions = queryOptions({
  queryKey: ["documents"],
  queryFn: ({ signal }) => fetchDocuments(signal),
});
