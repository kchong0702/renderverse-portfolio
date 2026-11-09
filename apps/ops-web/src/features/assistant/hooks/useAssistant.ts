import { useMutation } from "@tanstack/react-query";
import {
  answerTaskMutationOptions,
  sendMessageMutationOptions,
} from "../queries/assistant";

export function useSendMessage() {
  return useMutation(sendMessageMutationOptions);
}

export function useAnswerTask() {
  return useMutation(answerTaskMutationOptions);
}
