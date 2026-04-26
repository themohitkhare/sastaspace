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
        "src/app/**",          // Next.js server/page components — not unit-testable
        "src/lib/spacetime.ts", // dynamic-loaded SDK glue, not unit-testable
        "src/lib/projects.ts", // ditto
      ],
      thresholds: {
        lines: 50,
        functions: 55,
        statements: 50,
        branches: 50,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@sastaspace/stdb-bindings": path.resolve(
        __dirname,
        "../../packages/stdb-bindings/src/index.ts"
      ),
    },
  },
});
