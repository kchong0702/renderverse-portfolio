/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_EZBOT_API_URL: string;
  readonly VITE_SECRET_ROOM_PASSWORD: string;
  readonly VITE_CHATBOT_ENABLED: string;
  readonly VITE_PORT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
