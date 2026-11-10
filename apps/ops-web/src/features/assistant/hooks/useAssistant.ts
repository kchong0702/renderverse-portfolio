import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import {
  answerTaskMutationOptions,
  documentsQueryOptions,
  resumeTurnMutationOptions,
  sendMessageMutationOptions,
  stopMutationOptions,
} from "../queries/assistant";
import { openTurn, useAssistantStore } from "../state/assistantStore";

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

export function useResumeTurn() {
  const client = useQueryClient();
  const { mutate: resume } = useMutation(resumeTurnMutationOptions);

  useEffect(() => {
    if (client.isMutating({ mutationKey: ["assistant"] })) return;
    const { chatId, entries } = useAssistantStore.getState();
    const lastEventId = openTurn(entries)?.lastEventId;
    if (lastEventId) resume({ chatId, lastEventId });
  }, [client, resume]);
}
