import { test, expect } from '@playwright/test';

/* Per-page render checks live in all_pages.spec.ts (correct routes, no /rageval/ prefix —
   this file previously duplicated them under a wrong URL prefix that fell through to the
   catch-all route, so every test there trivially passed regardless of the page it claimed
   to check). Kept here: cross-cutting UI/UX properties that apply site-wide, verified
   against the real index.html / CSS rather than assumed. */

test.describe('2026 UI/UX Standards Validation', () => {
  test('Buttons show a pressed-state transform on mousedown', async ({ page }) => {
    // /evaluate always has real, data-independent buttons ("Use sample input", "Score");
    // the Overview page's buttons are conditional on having tracked data, which a fresh
    // deployment won't have yet.
    await page.goto('/evaluate');
    const btn = page.locator('button:visible').first();
    await expect(btn).toBeVisible();
    const box = await btn.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      const transform = await btn.evaluate((el) => window.getComputedStyle(el).transform);
      expect(transform).not.toBe('none');
      await page.mouse.up();
    }
  });

  test('Inputs show a visible focus ring', async ({ page }) => {
    await page.goto('/evaluate');
    const input = page.locator('textarea, input').first();
    await expect(input).toBeVisible();
    await input.focus();
    const style = await input.evaluate((el) => {
      const s = window.getComputedStyle(el);
      return { outline: s.outline, boxShadow: s.boxShadow, borderColor: s.borderColor };
    });
    const hasFocusIndicator = style.outline !== 'none' || style.boxShadow !== 'none';
    expect(hasFocusIndicator).toBe(true);
  });

  test('Mobile viewport meta matches the real index.html configuration', async ({ page }) => {
    await page.goto('/');
    const viewport = await page.locator('meta[name="viewport"]').getAttribute('content');
    expect(viewport).toContain('width=device-width');
    expect(viewport).toContain('shrink-to-fit=no');
    expect(viewport).toContain('maximum-scale=5.0');
  });
});
