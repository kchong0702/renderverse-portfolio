export const CONFIG = {
  ezbotApiUrl: import.meta.env.VITE_EZBOT_API_URL,
  secretRoomPassword: import.meta.env.VITE_SECRET_ROOM_PASSWORD,
  isChatbotEnabled: import.meta.env.VITE_CHATBOT_ENABLED === "true",
  portfolioBucketUrl: import.meta.env.VITE_PORTFOLIO_BUCKET_URL ?? "",
  portfolioUserId: import.meta.env.VITE_PORTFOLIO_USER_ID,
  languageStorageKey: "renderverse:lang",
};
