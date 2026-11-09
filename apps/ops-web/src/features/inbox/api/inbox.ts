import { http } from "@/shared/api/http";

export interface InboxMessage {
  id: string;
  thread_id: string;
  from_name: string;
  from_email: string;
  subject: string;
  snippet: string;
  received_at: string;
  unread: boolean;
}

export interface InboxMessageDetail extends InboxMessage {
  to: string;
  body: string;
}

const URL = "/ops-api/v1/inbox";

export const fetchInbox = (signal?: AbortSignal) =>
  http.get<InboxMessage[]>(URL, signal);

export const fetchMessage = (id: string, signal?: AbortSignal) =>
  http.get<InboxMessageDetail>(`${URL}/${id}`, signal);
