import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@/lib/utils": path.resolve(__dirname, "./src/lib/utils"),
      "@/components": path.resolve(__dirname, "./src/components"),
    },
  },
  build: {
    outDir: "dist",
    // Inline small assets to reduce file count
    assetsInlineLimit: 8192,
    rollupOptions: {
      output: {
        // Keep asset names predictable
        assetFileNames: "assets/[name]-[hash][extname]",
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
      },
    },
  },
});
