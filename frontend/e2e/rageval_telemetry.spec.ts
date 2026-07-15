import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:5173';

test.describe('Phase 4: RAGeval Telemetry & Tooling', () => {

  test('Slice 4.1: Overview & Cost Thresholds Rendering', async ({ page }) => {
    // 1. Check Overview Page
    await page.goto(`${BASE_URL}/`);
    await expect(page.locator('text=/RAGeval/i').first()).toBeVisible();
    await expect(page.locator('canvas, .recharts-wrapper, .kpi-grid').first()).toBeVisible({ timeout: 10000 });

    // 2. Check Cost Monitoring & Sliders
    await page.goto(`${BASE_URL}/cost`);
    await expect(page.locator('text=/Cost/i').first()).toBeVisible();
    
    // Check if the threshold slider or cost tables are visible
    const sliderOrTable = page.locator('input[type="range"], table, [role="grid"]');
    await expect(sliderOrTable.first()).toBeVisible();
  });

  test('Slice 4.1: Traces & Instrumentation Expansion', async ({ page }) => {
    // 1. Traces view
    await page.goto(`${BASE_URL}/traces`);
    await expect(page.locator('text=/Traces/i').first()).toBeVisible();
    
    // Traces usually have details/summary elements to expand JSON logs
    const details = page.locator('details');
    if (await details.count() > 0) {
      await details.first().click();
      // Ensure the JSON viewer or content expands
      await expect(details.first().locator('pre, code, .json-viewer')).toBeVisible();
    }

    // 2. Instrumentation
    await page.goto(`${BASE_URL}/instrumentation`);
    await expect(page.locator('text=/Instrumentation/i').first()).toBeVisible();
    await expect(page.locator('pre, code').first()).toBeVisible(); // Usually displays setup code snippets
  });

  test('Slice 4.1: Model & Evaluation Workflows', async ({ page }) => {
    const evalPages = [
      { path: '/evaluate', title: 'Evaluate' },
      { path: '/experiments', title: 'Experiments' },
      { path: '/models', title: 'Models' },
      { path: '/queries', title: 'Queries' },
      { path: '/alerts', title: 'Alerts' },
      { path: '/saved', title: 'Saved' }
    ];

    for (const ep of evalPages) {
      await test.step(`Verify ${ep.title} Rendering`, async () => {
        await page.goto(`${BASE_URL}${ep.path}`);
        await expect(page.locator('body')).toBeVisible();
        await expect(page.locator(`text=/${ep.title}/i`).first()).toBeVisible({ timeout: 5000 });
        
        // Ensure no fatal React crashes
        await expect(page.locator('text=/An unexpected error occurred/i')).toHaveCount(0);
      });
    }
  });

});
