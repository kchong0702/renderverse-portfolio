import { useMutation, useQuery } from "@tanstack/react-query";
import {
  answerTaskMutationOptions,
  documentsQueryOptions,
  sendMessageMutationOptions,
  stopMutationOptions,
} from "../queries/assistant";

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
