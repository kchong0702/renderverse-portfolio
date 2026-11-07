import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig(({ mode }) =>
  mode === "print"
    ? {
        plugins: [react()],
        base: "./",
        build: { outDir: "dist/print", chunkSizeWarningLimit: 1000 },
      }
    : {
        plugins: [react()],
        build: {
          outDir: "dist/lib",
          lib: {
            entry: "src/index.ts",
            formats: ["es"],
            fileName: "document-renderer",
          },
          rollupOptions: {
            external: ["react", "react-dom", "react/jsx-runtime"],
          },
        },
      },
);
