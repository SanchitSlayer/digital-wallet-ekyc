import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // The whole project shares the root .env, so VITE_API_URL is read from there.
  envDir: "..",
  server: { port: 5173, strictPort: true },
});
