import { CONFIG } from "../../config-global";

export async function connect() {
  return new WebSocket(CONFIG.websocketServerUrl);
}
