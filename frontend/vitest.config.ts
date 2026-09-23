import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // e2e/ holds Playwright specs (run via `npm run test:e2e`), not
    // vitest ones -- without this exclude, vitest's default glob picks
    // them up too and fails to load them (found live: `npx vitest run`
    // reported "Playwright Test did not expect test.describe() to be
    // called here" for frontend/e2e/upload.spec.ts).
    exclude: ["**/node_modules/**", "e2e/**"],
  },
});
