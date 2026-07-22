# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: rageval_telemetry.spec.ts >> Phase 5.1 — RAGeval UI Telemetry >> All main pages render without crash
- Location: e2e/rageval_telemetry.spec.ts:34:3

# Error details

```
Error: page.goto: net::ERR_NAME_NOT_RESOLVED at https://alerts/
Call log:
  - navigating to "https://alerts/", waiting until "load"

```

# Test source

```ts
  1   | import { test, expect, Page } from '@playwright/test';
  2   | 
  3   | /**
  4   |  * RAGeval — Comprehensive E2E Suite
  5   |  * Phase 5.1: RAGeval Telemetry & Monitoring
  6   |  * Phase 6: Extended UI/UX
  7   |  * Phase 8: Deep Component Integration (Embeddings, Vector Store)
  8   |  */
  9   | 
  10  | const BASE_URL = process.env.RAGEVAL_URL    || process.env.TEST_BASE_URL || '/';
  11  | const API_URL  = process.env.RAGEVAL_API_URL || '/';
  12  | const AUTH_URL = process.env.INTELAI_API_URL || '/';
  13  | 
  14  | async function getAuthToken(request: any): Promise<string> {
  15  |   const resp = await request.post(`${AUTH_URL}/api/login`, {
  16  |     data: { username: 'admin', password: 'fLNtwDH2VaQLbO' }
  17  |   }).catch(() => null);
  18  |   if (resp && resp.ok()) {
  19  |     const body = await resp.json();
  20  |     return body.access_token || body.token || '';
  21  |   }
  22  |   return '';
  23  | }
  24  | 
  25  | async function assertNoReactCrash(page: Page) {
  26  |   await expect(page.locator('text=/An unexpected error occurred|Something went wrong/i')).toHaveCount(0);
  27  | }
  28  | 
  29  | // ─────────────────────────────────────────────────────────────────────────────
  30  | // Phase 5.1 — RAGeval UI Workflows
  31  | // ─────────────────────────────────────────────────────────────────────────────
  32  | test.describe('Phase 5.1 — RAGeval UI Telemetry', () => {
  33  | 
  34  |   test('All main pages render without crash', async ({ page }) => {
  35  |     await page.goto(`${BASE_URL}/`);
  36  |     const routes = [
  37  |       '/alerts', '/cost', '/evaluate', '/experiments',
  38  |       '/instrumentation', '/models', '/overview', '/queries', '/saved', '/traces'
  39  |     ];
  40  |     for (const route of routes) {
> 41  |       await page.goto(`${'/'}${route}`);
      |                  ^ Error: page.goto: net::ERR_NAME_NOT_RESOLVED at https://alerts/
  42  |       await page.waitForLoadState('domcontentloaded');
  43  |       await assertNoReactCrash(page);
  44  |       console.log(`✅ RAGeval ${route} — OK`);
  45  |     }
  46  |   });
  47  | 
  48  |   test('Cost page: cost threshold slider triggers UI warning badge', async ({ page }) => {
  49  |     await page.goto(`${BASE_URL}/cost`);
  50  |     await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
  51  |     await assertNoReactCrash(page);
  52  | 
  53  |     // Look for a range slider
  54  |     const slider = page.locator('input[type="range"]').first();
  55  |     if (await slider.isVisible({ timeout: 5000 }).catch(() => false)) {
  56  |       // Move slider to minimum to trigger warnings
  57  |       await slider.fill('0.01');
  58  |       await page.waitForTimeout(1000);
  59  |       await assertNoReactCrash(page);
  60  |       // Optionally check for warning badge
  61  |       const warningBadge = page.locator('.badge, .warning, text=/warning|exceeded|threshold/i').first();
  62  |       if (await warningBadge.isVisible({ timeout: 3000 }).catch(() => false)) {
  63  |         await expect(warningBadge).toBeVisible();
  64  |       }
  65  |     }
  66  |   });
  67  | 
  68  |   test('Traces page: clicking a trace row expands detail view', async ({ page }) => {
  69  |     await page.goto(`${BASE_URL}/traces`);
  70  |     await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
  71  |     await assertNoReactCrash(page);
  72  | 
  73  |     // Look for a table row
  74  |     const row = page.locator('tr, .trace-row, [data-testid="trace-row"]').nth(1);
  75  |     if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
  76  |       await row.click();
  77  |       await page.waitForTimeout(1000);
  78  |       // After clicking, detail panel or expanded row should appear
  79  |       const detail = page.locator('.detail, .expanded, pre, code, [data-testid="trace-detail"]').first();
  80  |       if (await detail.isVisible({ timeout: 3000 }).catch(() => false)) {
  81  |         await expect(detail).toBeVisible();
  82  |       }
  83  |       await assertNoReactCrash(page);
  84  |     }
  85  |   });
  86  | 
  87  |   test('Experiments page: model comparison renders', async ({ page }) => {
  88  |     await page.goto(`${BASE_URL}/experiments`);
  89  |     await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
  90  |     await assertNoReactCrash(page);
  91  | 
  92  |     const compareEl = page.locator('table, .comparison, canvas, svg').first();
  93  |     if (await compareEl.isVisible({ timeout: 8000 }).catch(() => false)) {
  94  |       await expect(compareEl).toBeVisible();
  95  |     }
  96  |   });
  97  | });
  98  | 
  99  | // ─────────────────────────────────────────────────────────────────────────────
  100 | // Phase 5.1 — RAGeval API Tests
  101 | // ─────────────────────────────────────────────────────────────────────────────
  102 | test.describe('Phase 5.1 — RAGeval API Validation', () => {
  103 | 
  104 |   test('GET /health returns < 500', async ({ request }) => {
  105 |     const resp = await request.get(`${API_URL}/health`).catch(() => null);
  106 |     if (resp) expect(resp.status()).toBeLessThan(500);
  107 |   });
  108 | 
  109 |   test('GET /api/evaluations requires auth', async ({ request }) => {
  110 |     const resp = await request.get(`${API_URL}/api/evaluations`).catch(() => null);
  111 |     if (resp) expect([200, 401, 403, 404]).toContain(resp.status());
  112 |   });
  113 | 
  114 |   test('POST /api/evaluate with valid payload returns non-500', async ({ request }) => {
  115 |     const token = await getAuthToken(request);
  116 |     if (!token) { test.skip(); return; }
  117 | 
  118 |     const resp = await request.post(`${API_URL}/api/evaluate`, {
  119 |       headers: { Authorization: `Bearer ${token}` },
  120 |       data: {
  121 |         question: 'What is the quarterly revenue?',
  122 |         answer:   'The quarterly revenue is $1.2M.',
  123 |         contexts: ['Revenue report Q4: $1.2M total revenue across all divisions.'],
  124 |       },
  125 |       timeout: 30000,
  126 |     }).catch(() => null);
  127 | 
  128 |     if (resp) {
  129 |       expect(resp.status()).not.toBe(500);
  130 |       console.log(`RAGeval /api/evaluate → ${resp.status()}`);
  131 |     }
  132 |   });
  133 | 
  134 |   test('GET /api/traces returns list or empty', async ({ request }) => {
  135 |     const token = await getAuthToken(request);
  136 |     const resp = await request.get(`${API_URL}/api/traces`, {
  137 |       headers: token ? { Authorization: `Bearer ${token}` } : {}
  138 |     }).catch(() => null);
  139 |     if (resp) expect([200, 401, 403, 404]).toContain(resp.status());
  140 |   });
  141 | 
```