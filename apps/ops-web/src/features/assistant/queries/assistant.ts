import { mutationOptions } from "@tanstack/react-query";
import { answerTask, sendMessage, type TaskAnswer } from "../api/assistant";
import { useAssistantStore } from "../state/assistantStore";

const { add, restore } = useAssistantStore.getState();

export const sendMessageMutationOptions = mutationOptions({
  mutationKey: ["assistant", "send"],
  mutationFn: sendMessage,
  onMutate: ({ text }) => add({ role: "user", text }),
  onSuccess: (reply) => add({ role: "assistant", reply }),
  onError: (error) =>
    add({
      role: "assistant",
      reply: { status: "failed", reason: error.message },
    }),
});

export const answerTaskMutationOptions = mutationOptions({
  mutationKey: ["assistant", "answer"],
  mutationFn: answerTask,
  onMutate: ({ shown }: TaskAnswer) => {
    const previous = useAssistantStore.getState().entries;
    add({ role: "user", text: shown });
    return { previous };
  },
  onSuccess: (reply) => add({ role: "assistant", reply }),
  onError: (_error, _answer, result) => {
    if (result) restore(result.previous);
  },
});
