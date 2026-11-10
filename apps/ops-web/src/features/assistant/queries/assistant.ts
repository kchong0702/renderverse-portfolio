import { mutationOptions, queryOptions } from "@tanstack/react-query";
import i18n from "@/i18n";
import { ApiError } from "@/shared/api/http";
import { queryClient } from "@/shared/api/queryClient";
import {
  answerTask,
  cancelTask,
  fetchDocuments,
  resumeTurn,
  sendMessage,
  type Chat,
  type ChatMessage,
  type RunEvent,
  type Task,
  type TaskAnswer,
  type TurnCursor,
} from "../api/assistant";
import { useAssistantStore } from "../state/assistantStore";

export const documentsQueryOptions = queryOptions({
  queryKey: ["documents"],
  queryFn: ({ signal }) => fetchDocuments(signal),
});

const { add, apply, restore } = useAssistantStore.getState();

const streamControllers = new Map<string, AbortController>();

const newStreamSignal = (chat: Chat) => {
  const controller = new AbortController();
  streamControllers.set(chat.id, controller);
  return controller.signal;
};

const startTurn = (chat: Chat) => {
  add(chat, {
    role: "assistant",
    taskId: null,
    lastEventId: null,
    parts: [],
    outcome: null,
  });
  return newStreamSignal(chat);
};

const receive = (chat: Chat) => (event: RunEvent, id?: string) => {
  apply(chat, event, id);
  if (event.status !== "changeset") return;
  const document = [...documentsQueryOptions.queryKey, event.document_id];
  void Promise.all([
    queryClient.invalidateQueries({ queryKey: [...document, "changesets"] }),
    queryClient.invalidateQueries({ queryKey: document, exact: true }),
    queryClient.invalidateQueries({
      queryKey: documentsQueryOptions.queryKey,
      exact: true,
    }),
  ]);
};

const failTurn = (error: Error, { chat }: { chat: Chat }) =>
  apply(chat, { status: "failed", reason: error.message });

export const sendMessageMutationOptions = mutationOptions({
  mutationKey: ["assistant", "send"],
  mutationFn: (message: ChatMessage) =>
    sendMessage(message, startTurn(message.chat), receive(message.chat)),
  onMutate: ({ chat, text }) => add(chat, { role: "user", text }),
  onError: failTurn,
});

export const answerTaskMutationOptions = mutationOptions({
  mutationKey: ["assistant", "answer"],
  mutationFn: (answer: TaskAnswer) =>
    answerTask(answer, startTurn(answer.chat), receive(answer.chat)),
  onMutate: ({ chat, shown }) => {
    const previous =
      useAssistantStore.getState().chats[chat.kind][chat.id] ?? [];
    add(chat, { role: "user", text: shown });
    return { previous };
  },
  onError: (error, answer, result) =>
    error instanceof ApiError && result
      ? restore(answer.chat, result.previous)
      : failTurn(error, answer),
});

export const resumeTurnMutationOptions = mutationOptions({
  mutationKey: ["assistant", "resume"],
  mutationFn: (turn: TurnCursor) =>
    resumeTurn(turn, newStreamSignal(turn.chat), receive(turn.chat)),
  onError: (error, turn) =>
    error instanceof ApiError && error.status === 404
      ? apply(turn.chat, {
          status: "failed",
          reason: i18n.t("assistant.ended"),
        })
      : failTurn(error, turn),
});

export const stopMutationOptions = mutationOptions({
  mutationKey: ["assistant", "stop"],
  mutationFn: (task: Task) => cancelTask(task),
  onSuccess: (_stopped, { chat }) => {
    apply(chat, { status: "cancelled" });
    streamControllers.get(chat.id)?.abort();
  },
});
