import { mutationOptions } from "@tanstack/react-query";
import i18n from "@/i18n";
import { ApiError } from "@/shared/api/http";
import {
  answerTask,
  cancelTask,
  sendMessage,
  type ChatMessage,
  type TaskAnswer,
} from "../api/assistant";
import { useAssistantStore } from "../state/assistantStore";

const { add, apply, restore } = useAssistantStore.getState();

let run = new AbortController();

const start = () => {
  run = new AbortController();
  add({ role: "assistant", taskId: null, parts: [], outcome: null });
  return run.signal;
};

const halt = () => {
  apply({ status: "cancelled" });
  run.abort();
};

addEventListener("pagehide", halt);

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
  onSettled: halt,
});
