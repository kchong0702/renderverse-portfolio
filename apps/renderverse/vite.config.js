import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import eslint from "vite-plugin-eslint";

// https://vitejs.dev/config/
export default ({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  return defineConfig({
    plugins: [react(), eslint()],
    server: {
      host: true,
      port: Number(env.VITE_PORT) || 5173,
      watch: {
        usePolling: true, // windows hot reload
      },
    },
  });
};
