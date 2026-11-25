import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      // Same-origin in dev: the browser talks to :5173 and Vite forwards /api to Django.
      // That lets the HttpOnly SameSite=Strict refresh cookie work (no CORS involved).
      proxy: {
        "/api": {
          target: env.VITE_PROXY_TARGET || "http://127.0.0.1:8000",
          changeOrigin: false,
        },
      },
    },
  };
});
