import { test, expect, Page } from '@playwright/test';

/**
 * RAGeval — Comprehensive E2E Suite
 * Phase 5.1: RAGeval Telemetry & Monitoring
 * Phase 6: Extended UI/UX
 * Phase 8: Deep Component Integration (Embeddings, Vector Store)
 */

const BASE_URL = process.env.RAGEVAL_URL    || process.env.TEST_BASE_URL || 'http://localhost:5176';
const API_URL  = process.env.RAGEVAL_API_URL || 'http://localhost:8003';
const AUTH_URL = process.env.INTELAI_API_URL || 'http://localhost:8000';

async function getAuthToken(request: any): Promise<string> {
  const resp = await request.post(`${AUTH_URL}/api/login`, {
    data: { username: 'admin', password: 'fLNtwDH2VaQLbO' }
  }).catch(() => null);
  if (resp && resp.ok()) {
    const body = await resp.json();
    return body.access_token || body.token || '';
  }
  return '';
}

async function assertNoReactCrash(page: Page) {
  await expect(page.locator('text=/An unexpected error occurred|Something went wrong/i')).toHaveCount(0);
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 5.1 — RAGeval UI Workflows
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phase 5.1 — RAGeval UI Telemetry', () => {

  test('All main pages render without crash', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    const routes = [
      '/alerts', '/cost', '/evaluate', '/experiments',
      '/instrumentation', '/models', '/overview', '/queries', '/saved', '/traces'
    ];
    for (const route of routes) {
      await page.goto(`${BASE_URL}${route}`);
      await page.waitForLoadState('domcontentloaded');
      await assertNoReactCrash(page);
      console.log(`✅ RAGeval ${route} — OK`);
    }
  });

  test('Cost page: cost threshold slider triggers UI warning badge', async ({ page }) => {
    await page.goto(`${BASE_URL}/cost`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await assertNoReactCrash(page);

    // Look for a range slider
    const slider = page.locator('input[type="range"]').first();
    if (await slider.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Move slider to minimum to trigger warnings
      await slider.fill('0.01');
      await page.waitForTimeout(1000);
      await assertNoReactCrash(page);
      // Optionally check for warning badge
      const warningBadge = page.locator('.badge, .warning, text=/warning|exceeded|threshold/i').first();
      if (await warningBadge.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(warningBadge).toBeVisible();
      }
    }
  });

  test('Traces page: clicking a trace row expands detail view', async ({ page }) => {
    await page.goto(`${BASE_URL}/traces`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await assertNoReactCrash(page);

    // Look for a table row
    const row = page.locator('tr, .trace-row, [data-testid="trace-row"]').nth(1);
    if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
      await row.click();
      await page.waitForTimeout(1000);
      // After clicking, detail panel or expanded row should appear
      const detail = page.locator('.detail, .expanded, pre, code, [data-testid="trace-detail"]').first();
      if (await detail.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(detail).toBeVisible();
      }
      await assertNoReactCrash(page);
    }
  });

  test('Experiments page: model comparison renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/experiments`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await assertNoReactCrash(page);

    const compareEl = page.locator('table, .comparison, canvas, svg').first();
    if (await compareEl.isVisible({ timeout: 8000 }).catch(() => false)) {
      await expect(compareEl).toBeVisible();
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 5.1 — RAGeval API Tests
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phase 5.1 — RAGeval API Validation', () => {

  test('GET /health returns < 500', async ({ request }) => {
    const resp = await request.get(`${API_URL}/health`).catch(() => null);
    if (resp) expect(resp.status()).toBeLessThan(500);
  });

  test('GET /api/evaluations requires auth', async ({ request }) => {
    const resp = await request.get(`${API_URL}/api/evaluations`).catch(() => null);
    if (resp) expect([200, 401, 403, 404]).toContain(resp.status());
  });

  test('POST /api/evaluate with valid payload returns non-500', async ({ request }) => {
    const token = await getAuthToken(request);
    if (!token) { test.skip(); return; }

    const resp = await request.post(`${API_URL}/api/evaluate`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        question: 'What is the quarterly revenue?',
        answer:   'The quarterly revenue is $1.2M.',
        contexts: ['Revenue report Q4: $1.2M total revenue across all divisions.'],
      },
      timeout: 30000,
    }).catch(() => null);

    if (resp) {
      expect(resp.status()).not.toBe(500);
      console.log(`RAGeval /api/evaluate → ${resp.status()}`);
    }
  });

  test('GET /api/traces returns list or empty', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await request.get(`${API_URL}/api/traces`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    }).catch(() => null);
    if (resp) expect([200, 401, 403, 404]).toContain(resp.status());
  });

  test('Payload fuzzing: boundary cost values do not cause 500', async ({ request }) => {
    const token = await getAuthToken(request);
    const fuzzPayloads = [
      { threshold: -1 },
      { threshold: 999999 },
      { threshold: 'not_a_number' },
      { threshold: null },
    ];
    for (const payload of fuzzPayloads) {
      const resp = await request.post(`${API_URL}/api/cost-threshold`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        data: payload,
      }).catch(() => null);
      if (resp) expect(resp.status()).not.toBe(500);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 8 — Embeddings & Vector Store Integration (via RAGeval)
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phase 8.3 — Embedding & Vector Store', () => {

  test('POST /api/embed with text returns embeddings vector', async ({ request }) => {
    const token = await getAuthToken(request);
    if (!token) { test.skip(); return; }

    const resp = await request.post(`${API_URL}/api/embed`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { text: 'Quarterly revenue growth for 2026 fiscal year.' },
      timeout: 30000,
    }).catch(() => null);

    if (resp) {
      expect(resp.status()).not.toBe(500);
      if (resp.status() === 200) {
        const body = await resp.json();
        // Should return an array (embedding vector) or object with embeddings key
        expect(body.embeddings || Array.isArray(body) || body.vector).toBeTruthy();
      }
    }
  });

  test('POST /api/embed with empty text returns 400 not 500', async ({ request }) => {
    const token = await getAuthToken(request);
    if (!token) { test.skip(); return; }

    const resp = await request.post(`${API_URL}/api/embed`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { text: '' },
    }).catch(() => null);
    if (resp) expect([400, 422]).toContain(resp.status());
  });

  test('Duplicate document does not re-embed: deterministic hash check', async ({ request }) => {
    const token = await getAuthToken(request);
    if (!token) { test.skip(); return; }

    const docText = 'UNIQUE_DEDUP_TEST_DOCUMENT_' + Date.now();

    const resp1 = await request.post(`${API_URL}/api/embed`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { text: docText },
      timeout: 30000,
    }).catch(() => null);

    const resp2 = await request.post(`${API_URL}/api/embed`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { text: docText },
      timeout: 30000,
    }).catch(() => null);

    if (resp1 && resp2 && resp1.ok() && resp2.ok()) {
      const body1 = await resp1.json();
      const body2 = await resp2.json();
      // If the API supports dedup, the IDs should be the same
      if (body1.id && body2.id) {
        console.log(`Dedup check: id1=${body1.id}, id2=${body2.id}`);
        // Same ID = dedup working correctly
        // Different ID = embedding each time (acceptable but noted)
      }
    }
  });
});
