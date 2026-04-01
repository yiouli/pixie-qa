import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";
import { resolve } from "path";

// VITE_BUILD_TARGET selects which entry point to build:
//   "scorecard" (default) → index.html → ../pixie/assets/index.html
//   "webui"               → webui.html → ../pixie/assets/webui.html
const target = process.env.VITE_BUILD_TARGET ?? "scorecard";
const entry = target === "webui" ? "webui.html" : "index.html";

export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: "../pixie/assets",
    emptyOutDir: false,
    rollupOptions: {
      input: resolve(__dirname, entry),
    },
  },
});
