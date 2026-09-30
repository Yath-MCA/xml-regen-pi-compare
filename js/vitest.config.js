import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "happy-dom",
    include: ["__tests__/**/*.{test,spec}.{js,mjs,cjs}"],
    globals: false,
  },
});
