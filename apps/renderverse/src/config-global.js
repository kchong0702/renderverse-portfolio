export const CONFIG = {
  ezbotApiUrl: import.meta.env.VITE_EZBOT_API_URL,
  secretRoomPassword: import.meta.env.VITE_SECRET_ROOM_PASSWORD,
  isChatbotEnabled: import.meta.env.VITE_CHATBOT_ENABLED === "true",
  languageStorageKey: "renderverse:lang",
};
