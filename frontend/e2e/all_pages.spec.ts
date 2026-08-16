import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || '';

const ROUTES = ['/', '/evaluate', '/experiments', '/benchmark', '/traces', '/queries', '/models',
  '/alerts', '/cost', '/saved', '/instrumentation', '/api-docs', '/user-guide'];

test.describe('RAGeval All Pages E2E Suite', () => {

  test.beforeEach(async ({ page }) => {
    await page.route('**/*', async route => {
      const req = route.request();
      const url = req.url();
      // When the app is served from a static-hosted preview deployment, its fetch/XHR
      // calls still point at that hosted origin; redirect them to a local backend
      // for e2e testing instead.
      if ((req.resourceType() === 'fetch' || req.resourceType() === 'xhr') && url.includes('.app/')) {
        const backendUrl = process.env.TEST_BACKEND_URL || 'http://localhost:8003';
        const pathPart = new URL(url).pathname;
        const newUrl = backendUrl.replace(/\/$/, '') + pathPart;
        await route.continue({ url: newUrl });
      } else {
        await route.continue();
      }
    });
  });

  for (const route of ROUTES) {
    test(`Should successfully load ${route} page without crashing`, async ({ page }) => {
      await page.goto(route);
      // Wait for DOM to load
      await page.waitForLoadState('domcontentloaded');

      // Ensure the blank screen of death did not occur
      const rootHtml = await page.locator('#root').innerHTML();
      expect(rootHtml.length).toBeGreaterThan(0);

      // Ensure no generic "An unexpected error occurred" overlay
      const errorOverlay = page.locator('text=unexpected error');
      await expect(errorOverlay).not.toBeVisible();
    });
  }
});
