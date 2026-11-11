import type { Application } from "@/features/applications";
import type { InboxMessage } from "../api/inbox";

export interface Thread extends InboxMessage {
  application: Application | undefined;
}

export function threadsOf(
  messages: InboxMessage[],
  applications: Application[],
): Thread[] {
  return messages
    .filter(
      (message, index) =>
        messages.findIndex(
          ({ thread_id }) => thread_id === message.thread_id,
        ) === index,
    )
    .map((message) => ({
      ...message,
      unread: messages.some(
        ({ thread_id, unread }) => thread_id === message.thread_id && unread,
      ),
      application: applications.find(({ id }) => id === message.application_id),
    }));
}
