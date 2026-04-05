import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";
import { resolve } from "path";

export default defineConfig({
  plugins: [tailwindcss(), react(), viteSingleFile()],
  build: {
    outDir: "../pixie/assets",
    emptyOutDir: false,
    rollupOptions: {
      input: resolve(__dirname, "webui.html"),
    },
  },
});
