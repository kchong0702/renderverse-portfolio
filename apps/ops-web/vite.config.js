import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import eslint from "vite-plugin-eslint";

// https://vitejs.dev/config/
export default ({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return defineConfig({
    plugins: [react(), tailwindcss(), eslint()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      port: Number(env.VITE_PORT) || 5174,
      // Same path `tailscale serve` routes on the VM, so API calls stay relative
      proxy: {
        "/ops-api": env.OPS_API_PROXY_TARGET || "http://127.0.0.1:8100",
      },
    },
    // Proxies like the dev server; off renderverse's preview port (4173)
    preview: { port: 4174 },
  });
};
