import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import i18n from "@/i18n";
import { useEffect } from "react";
import type { Chat } from "../api/assistant";
import {
  answerTaskMutationOptions,
  documentsQueryOptions,
  resumeTurnMutationOptions,
  sendMessageMutationOptions,
  stopMutationOptions,
} from "../queries/assistant";
import { openTurn, useAssistantStore } from "../state/assistantStore";

export function useChat(): Chat {
  const document = useAssistantStore((state) => state.document);
  const chatId = useAssistantStore((state) => state.chatId);
  return document
    ? { kind: "document", id: document.id }
    : { kind: "assistant", id: chatId };
}

export function useSendMessage() {
  return useMutation(sendMessageMutationOptions);
}

export function useAnswerTask() {
  return useMutation(answerTaskMutationOptions);
}

export function useStop() {
  return useMutation(stopMutationOptions);
}

export function useDocuments() {
  return useQuery(documentsQueryOptions);
}

export function useResumeTurns() {
  const client = useQueryClient();
  const { mutate: resume } = useMutation(resumeTurnMutationOptions);
  const apply = useAssistantStore((state) => state.apply);

  useEffect(() => {
    if (client.isMutating({ mutationKey: ["assistant"] })) return;
    const { chats } = useAssistantStore.getState();
    for (const kind of ["assistant", "document"] as const)
      for (const [id, entries] of Object.entries(chats[kind])) {
        const turn = openTurn(entries ?? []);
        if (!turn) continue;
        const chat = { kind, id };
        if (turn.lastEventId) resume({ chat, lastEventId: turn.lastEventId });
        else
          apply(chat, { status: "failed", reason: i18n.t("assistant.ended") });
      }
  }, [apply, client, resume]);
}
