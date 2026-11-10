import type { Application } from "@/features/applications";
import type { InboxMessage } from "../api/inbox";

export interface Thread extends InboxMessage {
  application: Application | undefined;
}

const squash = (text: string) =>
  text.toLocaleLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

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
    .map((message) => {
      const sent = squash(
        `${message.from_name} ${message.from_email} ${message.subject}`,
      );
      return {
        ...message,
        unread: messages.some(
          ({ thread_id, unread }) => thread_id === message.thread_id && unread,
        ),
        application: applications.find(
          ({ company }) => squash(company) && sent.includes(squash(company)),
        ),
      };
    });
}
