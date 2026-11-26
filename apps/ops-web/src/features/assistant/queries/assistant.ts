import {
  infiniteQueryOptions,
  mutationOptions,
  queryOptions,
} from "@tanstack/react-query";
import i18n from "@/i18n";
import { ApiError } from "@/shared/api/http";
import { queryClient } from "@/shared/api/queryClient";
import {
  answerTask,
  cancelTask,
  decideTask,
  fetchChangesets,
  fetchDocuments,
  fetchSession,
  fetchThreadMessages,
  followTurn,
  sendMessage,
  sendRefused,
  startThread,
  type Chat,
  type ChatMessage,
  type Conversation,
  type RunEvent,
  type Task,
  type TaskAnswer,
  type TaskDecision,
} from "../api/assistant";
import { useAssistantStore } from "../state/assistantStore";

export const documentsQueryOptions = queryOptions({
  queryKey: ["documents"],
  queryFn: ({ signal }) => fetchDocuments(signal),
});

export const changesetsQueryOptions = (documentId: string) =>
  queryOptions({
    queryKey: ["documents", documentId, "changesets"],
    queryFn: ({ signal }) => fetchChangesets(documentId, signal),
  });

export const sessionQueryOptions = (conversation: Conversation) =>
  queryOptions({
    queryKey: ["agent", "sessions", conversation],
    queryFn: ({ signal }) => fetchSession(conversation, signal),
    staleTime: Infinity,
  });

export const threadMessagesQueryOptions = ({
  threadId,
}: Pick<Chat, "threadId">) =>
  infiniteQueryOptions({
    queryKey: ["agent", "threads", threadId, "messages"],
    queryFn: async ({ pageParam, signal }) => {
      const covers =
        pageParam === null
          ? (useAssistantStore.getState().live[threadId] ?? []).filter(
              (entry) => entry.role === "user" || entry.outcome,
            )
          : [];
      return {
        ...(await fetchThreadMessages({ threadId, before: pageParam }, signal)),
        covers,
      };
    },
    initialPageParam: null as string | null,
    getNextPageParam: (page) =>
      page.has_more ? page.messages[0]?.id : undefined,
    gcTime: Infinity,
    refetchOnWindowFocus: "always",
  });

const { add, apply, reconnect, restore } = useAssistantStore.getState();

const streamControllers = new Map<string, AbortController>();

const startTurn = ({ threadId }: Chat) => {
  add(threadId, {
    role: "assistant",
    id: crypto.randomUUID(),
    taskId: null,
    parts: [],
    outcome: null,
    startedAt: Date.now(),
    endedAt: null,
    connection: { status: "connected" },
  });
  const controller = new AbortController();
  streamControllers.set(threadId, controller);
  return controller.signal;
};

const receive =
  ({ threadId }: Chat) =>
  (event: RunEvent) => {
    apply(threadId, event);
    if (
      event.status === "step" &&
      event.step.status === "done" &&
      event.step.name === "assign_career_consultant_task"
    ) {
      void queryClient.invalidateQueries({
        queryKey: documentsQueryOptions.queryKey,
      });
      return;
    }
    if (event.status === "profile_saved") {
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ["profile"] }),
        queryClient.invalidateQueries({ queryKey: ["portfolio"] }),
      ]);
      return;
    }
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

const onReconnect =
  ({ threadId }: Chat) =>
  (attempt: number) =>
    reconnect(threadId, attempt);

const failTurn = (error: Error, { chat }: { chat: Chat }) =>
  apply(chat.threadId, { status: "failed", reason: error.message });

const liveEntries = ({ threadId }: Chat) =>
  useAssistantStore.getState().live[threadId] ?? [];

export const sendMessageMutationOptions = mutationOptions({
  mutationKey: ["assistant", "send"],
  mutationFn: (message: ChatMessage) =>
    sendMessage(
      message,
      startTurn(message.chat),
      receive(message.chat),
      onReconnect(message.chat),
    ),
  onMutate: ({ chat, text }) => {
    const previous = liveEntries(chat);
    add(chat.threadId, {
      role: "user",
      id: crypto.randomUUID(),
      text,
    });
    return { previous };
  },
  onError: (error, message, result) => {
    if (!sendRefused(error) || !result) return failTurn(error, message);
    restore(message.chat.threadId, result.previous);
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ["agent", "sessions"] }),
      queryClient.invalidateQueries({
        queryKey: threadMessagesQueryOptions(message.chat).queryKey,
      }),
    ]);
  },
});

export const answerTaskMutationOptions = mutationOptions({
  mutationKey: ["assistant", "answer"],
  mutationFn: (answer: TaskAnswer) =>
    answerTask(
      answer,
      startTurn(answer.chat),
      receive(answer.chat),
      onReconnect(answer.chat),
    ),
  onMutate: ({ chat, shown }) => {
    const previous = liveEntries(chat);
    add(chat.threadId, {
      role: "user",
      id: crypto.randomUUID(),
      text: shown,
      answered: true,
    });
    return { previous };
  },
  onError: (error, answer, result) =>
    error instanceof ApiError && result
      ? restore(answer.chat.threadId, result.previous)
      : failTurn(error, answer),
});

export const decideMutationOptions = mutationOptions({
  mutationKey: ["assistant", "decide"],
  mutationFn: (task: TaskDecision) =>
    decideTask(
      task,
      startTurn(task.chat),
      receive(task.chat),
      onReconnect(task.chat),
    ),
  onMutate: ({ chat, decision }) => {
    const previous = liveEntries(chat);
    add(chat.threadId, {
      role: "user",
      id: crypto.randomUUID(),
      text: decision.message ?? "",
      answered: true,
      decision: decision.approve ? "approve" : "reject",
    });
    return { previous };
  },
  onError: (error, task, result) =>
    error instanceof ApiError && result
      ? restore(task.chat.threadId, result.previous)
      : failTurn(error, task),
});

const follow = (chat: Chat) =>
  followTurn(chat, startTurn(chat), receive(chat), onReconnect(chat)).catch(
    (error: Error) =>
      error instanceof ApiError && error.status === 404
        ? apply(chat.threadId, {
            status: "failed",
            reason: i18n.t("assistant.ended"),
          })
        : failTurn(error, { chat }),
  );

export const followTurnMutationOptions = mutationOptions({
  mutationKey: ["assistant", "follow"],
  mutationFn: follow,
});

export const followDocumentMutationOptions = mutationOptions({
  mutationKey: ["assistant", "follow-document"],
  mutationFn: async (documentId: string) => {
    const { thread_id: threadId } = await queryClient.fetchQuery(
      sessionQueryOptions({ agent: "career-consultant", documentId }),
    );
    const history = await queryClient.fetchInfiniteQuery(
      threadMessagesQueryOptions({ threadId }),
    );
    if (history.pages[0]?.messages.at(-1)?.role === "user")
      await follow({ threadId });
  },
});

export const stopMutationOptions = mutationOptions({
  mutationKey: ["assistant", "stop"],
  mutationFn: (task: Task) => cancelTask(task),
  onSuccess: (_stopped, { chat }) => {
    apply(chat.threadId, { status: "cancelled" });
    streamControllers.get(chat.threadId)?.abort();
  },
});

export const clearConversationMutationOptions = mutationOptions({
  mutationKey: ["agent", "clear"],
  mutationFn: startThread,
  onSuccess: (session, conversation) =>
    queryClient.setQueryData(
      sessionQueryOptions(conversation).queryKey,
      session,
    ),
});
