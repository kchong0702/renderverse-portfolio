import { request } from "../client";
import { CHAT_STOP_PATH } from "./constants";

export async function stopChat(): Promise<void> {
  await request(CHAT_STOP_PATH, { method: "POST" }).catch(() => {});
}
