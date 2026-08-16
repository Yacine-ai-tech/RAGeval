import { defineConfig } from "vite";
import { configDefaults } from "vitest/config";
import react from "@vitejs/plugin-react";

// Dev: `VITE_PROXY_TARGET=http://localhost:8000 npm run dev` proxies API calls to a
// running backend (local uvicorn or your deployed backend's URL). Prod build is
// same-origin — FastAPI serves dist/ itself.
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8000";
// Regex keys, not plain string prefixes: Vite's string-key proxy matching is a plain
// prefix match, so a "/eval" key would also swallow the "/evaluate" client-side route
// (any GET to /evaluate got silently proxied to the backend's /eval/* namespace instead
// of falling through to the SPA) — anchor each to a path boundary instead.
const apiPathPatterns = ["^/health$", "^/eval(/|$)", "^/docs$", "^/openapi\\.json$"];

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      apiPathPatterns.map((p) => [p, { target, changeOrigin: true, secure: false }]),
    ),
  },
  build: {
    chunkSizeWarningLimit: 900,
  },
  test: {
    // e2e/ holds Playwright specs (npm run test:e2e) — vitest's default glob would
    // otherwise also try to collect them and fail on the missing @playwright/test runtime.
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
});
