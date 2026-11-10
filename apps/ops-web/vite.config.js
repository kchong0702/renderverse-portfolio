import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import eslint from "vite-plugin-eslint";

export default ({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return defineConfig({
    plugins: [
      react(),
      tailwindcss(),
      eslint({ include: ["src/**/*.{js,jsx,ts,tsx}"] }),
    ],
    resolve: {
      alias: [
        {
          find: "@",
          replacement: fileURLToPath(new URL("./src", import.meta.url)),
        },
        {
          find: /^@renderverse\/document-renderer$/,
          replacement: fileURLToPath(
            new URL(
              "../../packages/document-renderer/src/index.ts",
              import.meta.url,
            ),
          ),
        },
      ],
      dedupe: ["react", "react-dom"],
    },
    server: {
      port: Number(env.VITE_PORT) || 5174,
      proxy: {
        "/ops-api": env.OPS_API_PROXY_TARGET || "http://127.0.0.1:8100",
      },
    },
    preview: { port: 4174 },
  });
};
