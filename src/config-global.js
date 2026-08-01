export const CONFIG = {
  websocketServerUrl: import.meta.env.VITE_WEBSOCKET_SERVER_URL,
  secretRoomPassword: import.meta.env.VITE_SECRET_ROOM_PASSWORD,
  isChatbotEnabled: import.meta.env.VITE_CHATBOT_ENABLED === "true",
};
