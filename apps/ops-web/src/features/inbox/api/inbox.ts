import { http } from "@/shared/api/http";

export type ThreadState = "needs_reply" | "interview" | "offer" | "info";

export interface InboxMessage {
  id: string;
  thread_id: string;
  from_name: string;
  from_email: string;
  subject: string;
  snippet: string;
  received_at: string;
  unread: boolean;
  state: ThreadState | null;
  decide_by: string | null;
  application_id: string | null;
}

export interface InboxMessageDetail extends InboxMessage {
  to: string;
  body: string;
}

export interface InboxList {
  messages: InboxMessage[];
  needs_reply: number;
}

export interface Slot {
  start: string;
  end: string;
}

export interface Failed {
  status: "failed";
  reason: string;
  next: { label: string; screen: string } | null;
}

export interface Email {
  to: string;
  subject: string;
  body: string;
}

const URL = "/ops-api/v1/inbox";

export const fetchInbox = (signal?: AbortSignal) =>
  http.get<InboxList>(URL, signal);

export const fetchMessage = (id: string, signal?: AbortSignal) =>
  http.get<InboxMessageDetail>(`${URL}/${id}`, signal);

export const draftReply = (threadId: string) =>
  http.post<{ body: string; slots: Slot[] } | Failed>(
    `${URL}/${threadId}/reply-draft`,
  );

export const sendReply = ({
  threadId,
  body,
}: {
  threadId: string;
  body: string;
}) => http.post<void>(`${URL}/${threadId}/reply`, { body });

export const sendEmail = (email: Email) =>
  http.post<void>(`${URL}/compose`, email);

export const draftFollowUp = (applicationId: string) =>
  http.post<{ body: string } | Failed>(
    `/ops-api/v1/applications/${applicationId}/follow-up-draft`,
  );
