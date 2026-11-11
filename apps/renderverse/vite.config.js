import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import eslint from "vite-plugin-eslint";

// https://vitejs.dev/config/
export default ({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  return defineConfig({
    plugins: [
      react(),
      eslint(),
      {
        name: "ops-api-storage",
        apply: "serve",
        configureServer(server) {
          const storage = new URL("../ops-api/.data/storage", import.meta.url);
          server.middlewares.use((req, _res, next) => {
            if (req.url?.startsWith("/sites/")) {
              req.url = `/@fs${storage.pathname}${req.url}`;
            }
            next();
          });
        },
      },
    ],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      host: true,
      port: Number(env.VITE_PORT) || 5173,
      watch: {
        usePolling: true, // windows hot reload
      },
    },
  });
};
