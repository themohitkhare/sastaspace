import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./test/setup.ts"],
    css: true,
    include: ["test/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "json-summary"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/app/layout.tsx",
        "src/app/page.tsx", // server component — fs read at build, asserted by build success
        "src/app/[slug]/page.tsx", // server component — MDX render at build
        "src/lib/spacetime.ts", // dynamic SDK glue
        "src/lib/comments.ts", // dynamic SDK glue
        "src/lib/posts.ts", // node fs read at build
      ],
      thresholds: {
        lines: 60,
        functions: 60,
        statements: 60,
        branches: 50,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@sastaspace/stdb-bindings": path.resolve(
        __dirname,
        "../../packages/stdb-bindings/src/index.ts",
      ),
    },
  },
});
