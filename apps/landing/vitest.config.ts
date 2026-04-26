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
        "src/lib/spacetime.ts", // dynamic-loaded SDK glue, not unit-testable
        "src/lib/projects.ts", // ditto
      ],
      thresholds: {
        lines: 4,
        functions: 8,
        statements: 4,
        branches: 5,
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
