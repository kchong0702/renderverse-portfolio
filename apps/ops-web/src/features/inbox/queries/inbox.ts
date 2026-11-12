import { mutationOptions, queryOptions } from "@tanstack/react-query";
import { applicationsQueryOptions } from "@/features/applications";
import {
  draftFollowUp,
  draftReply,
  fetchInbox,
  fetchMessage,
  sendEmail,
  sendReply,
} from "../api/inbox";

export const inboxQueryOptions = queryOptions({
  queryKey: ["inbox"],
  queryFn: async ({ signal, client }) => {
    const inbox = await fetchInbox(signal);
    void client.invalidateQueries({
      queryKey: applicationsQueryOptions.queryKey,
    });
    return inbox;
  },
});

export const messageQueryOptions = (id: string) =>
  queryOptions({
    queryKey: ["inbox", id],
    queryFn: ({ signal }) => fetchMessage(id, signal),
    staleTime: Infinity,
  });

export const replyDraftQueryOptions = (threadId: string, messageId: string) =>
  queryOptions({
    queryKey: ["reply-draft", threadId, messageId],
    queryFn: () => draftReply(threadId),
    staleTime: Infinity,
  });

export const sendReplyMutationOptions = mutationOptions({
  mutationFn: sendReply,
  onSuccess: (_data, _variables, _result, { client }) =>
    client.invalidateQueries({ queryKey: inboxQueryOptions.queryKey }),
});

export const sendEmailMutationOptions = mutationOptions({
  mutationFn: sendEmail,
  onSuccess: (_data, _variables, _result, { client }) =>
    client.invalidateQueries({ queryKey: inboxQueryOptions.queryKey }),
});

export const draftFollowUpMutationOptions = mutationOptions({
  mutationFn: draftFollowUp,
});
