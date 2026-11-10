import { useMutation, useQuery } from "@tanstack/react-query";
import {
  draftFollowUpMutationOptions,
  inboxQueryOptions,
  messageQueryOptions,
  replyDraftQueryOptions,
  sendEmailMutationOptions,
  sendReplyMutationOptions,
} from "../queries/inbox";

export function useInbox(enabled: boolean) {
  return useQuery({ ...inboxQueryOptions, enabled });
}

export function useMessage(id: string) {
  return useQuery(messageQueryOptions(id));
}

export function useReplyDraft(threadId: string, messageId: string) {
  return useQuery(replyDraftQueryOptions(threadId, messageId));
}

export function useSendReply() {
  return useMutation(sendReplyMutationOptions);
}

export function useSendEmail() {
  return useMutation(sendEmailMutationOptions);
}

export function useDraftFollowUp() {
  return useMutation(draftFollowUpMutationOptions);
}
