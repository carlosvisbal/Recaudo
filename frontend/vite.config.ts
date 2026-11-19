import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: [
        "icons/icon-192.png",
        "icons/icon-512.png",
        "icons/icon-512-maskable.png",
        "apple-touch-icon.png",
        "favicon.ico",
        "favicon-32.png",
      ],
      manifest: {
        id: "/",
        name: "Recaudo",
        short_name: "Recaudo",
        description: "Control operativo de recaudos para PC, iPhone y Android",
        theme_color: "#1B84FF",
        background_color: "#F9F9F9",
        display: "standalone",
        display_override: ["standalone", "minimal-ui", "browser"],
        orientation: "any",
        start_url: "/",
        scope: "/",
        lang: "es-CO",
        dir: "ltr",
        categories: ["finance", "business", "productivity"],
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
          {
            src: "/icons/icon-512-maskable.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/salud\//, /^\/media\//],
        globPatterns: ["**/*.{js,css,html,svg,png,ico,webp,woff2}"],
        // No cachear API/media: la app siempre pide datos frescos con sesión.
        runtimeCaching: [],
        clientsClaim: true,
        skipWaiting: true,
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
      "/salud": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "../backend/static/frontend",
    emptyOutDir: true,
  },
});
