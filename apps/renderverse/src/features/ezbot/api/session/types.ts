export interface EzbotSession {
  /** Sent back in the session header on every chat request from this tab */
  session_id: string;
  /** Seconds without a message before the server ends the session */
  idle_ttl_s: number;
}
