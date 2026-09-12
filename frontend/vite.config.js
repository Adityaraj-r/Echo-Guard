import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";
import fs from "node:fs";

const useHttps = process.env.VITE_HTTPS === "true";
const host = process.env.VITE_HOST || "127.0.0.1";
const apiTarget = process.env.VITE_API_TARGET || "http://127.0.0.1:8000";
const httpsConfig =
  useHttps && process.env.VITE_HTTPS_KEY && process.env.VITE_HTTPS_CERT
    ? {
        key: fs.readFileSync(process.env.VITE_HTTPS_KEY),
        cert: fs.readFileSync(process.env.VITE_HTTPS_CERT),
      }
    : useHttps;

export default defineConfig({
  plugins: [react(), useHttps ? basicSsl() : null].filter(Boolean),
  server: {
    host,
    port: 5173,
    strictPort: true,
    https: httpsConfig,
    hmr: {
      host: host === "0.0.0.0" ? undefined : host,
    },
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/assets": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
