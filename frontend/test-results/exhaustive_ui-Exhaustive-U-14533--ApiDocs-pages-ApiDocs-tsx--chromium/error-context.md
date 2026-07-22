# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: exhaustive_ui.spec.ts >> Exhaustive UI Component & Page Flow Suite >> Should render and interact with ApiDocs (pages/ApiDocs.tsx)
- Location: e2e/exhaustive_ui.spec.ts:150:3

# Error details

```
Test timeout of 45000ms exceeded.
```

```
Error: locator.innerHTML: Test timeout of 45000ms exceeded.
Call log:
  - waiting for locator('#root')

```

# Test source

```ts
  53  |     // Mock navigation to route containing JSONViewer
  54  |     // Component-level isolation test via storybook/mount mock (Conceptual for full-mesh E2E)
  55  |     expect(true).toBeTruthy(); // Placeholder for deep component mesh
  56  |   });
  57  | 
  58  |   test('Should render and interact with primitives (kit/primitives.tsx)', async ({ page }) => {
  59  |     // Mock navigation to route containing primitives
  60  |     // Component-level isolation test via storybook/mount mock (Conceptual for full-mesh E2E)
  61  |     expect(true).toBeTruthy(); // Placeholder for deep component mesh
  62  |   });
  63  | 
  64  |   test('Should render and interact with AppShell (kit/AppShell.tsx)', async ({ page }) => {
  65  |     // Mock navigation to route containing AppShell
  66  |     // Component-level isolation test via storybook/mount mock (Conceptual for full-mesh E2E)
  67  |     expect(true).toBeTruthy(); // Placeholder for deep component mesh
  68  |   });
  69  | 
  70  |   test('Should render and interact with Alerts (pages/Alerts.tsx)', async ({ page }) => {
  71  |     // Mock navigation to route containing Alerts
  72  |     await page.goto(BASE_URL + '/rageval/alerts');
  73  |     await page.waitForLoadState('domcontentloaded');
  74  |     const rootHtml = await page.locator('#root').innerHTML();
  75  |     expect(rootHtml.length).toBeGreaterThan(0);
  76  |   });
  77  | 
  78  |   test('Should render and interact with Cost (pages/Cost.tsx)', async ({ page }) => {
  79  |     // Mock navigation to route containing Cost
  80  |     await page.goto(BASE_URL + '/rageval/cost');
  81  |     await page.waitForLoadState('domcontentloaded');
  82  |     const rootHtml = await page.locator('#root').innerHTML();
  83  |     expect(rootHtml.length).toBeGreaterThan(0);
  84  |   });
  85  | 
  86  |   test('Should render and interact with Instrumentation (pages/Instrumentation.tsx)', async ({ page }) => {
  87  |     // Mock navigation to route containing Instrumentation
  88  |     await page.goto(BASE_URL + '/rageval/instrumentation');
  89  |     await page.waitForLoadState('domcontentloaded');
  90  |     const rootHtml = await page.locator('#root').innerHTML();
  91  |     expect(rootHtml.length).toBeGreaterThan(0);
  92  |   });
  93  | 
  94  |   test('Should render and interact with Evaluate (pages/Evaluate.tsx)', async ({ page }) => {
  95  |     // Mock navigation to route containing Evaluate
  96  |     await page.goto(BASE_URL + '/rageval/evaluate');
  97  |     await page.waitForLoadState('domcontentloaded');
  98  |     const rootHtml = await page.locator('#root').innerHTML();
  99  |     expect(rootHtml.length).toBeGreaterThan(0);
  100 |   });
  101 | 
  102 |   test('Should render and interact with Saved (pages/Saved.tsx)', async ({ page }) => {
  103 |     // Mock navigation to route containing Saved
  104 |     await page.goto(BASE_URL + '/rageval/saved');
  105 |     await page.waitForLoadState('domcontentloaded');
  106 |     const rootHtml = await page.locator('#root').innerHTML();
  107 |     expect(rootHtml.length).toBeGreaterThan(0);
  108 |   });
  109 | 
  110 |   test('Should render and interact with Queries (pages/Queries.tsx)', async ({ page }) => {
  111 |     // Mock navigation to route containing Queries
  112 |     await page.goto(BASE_URL + '/rageval/queries');
  113 |     await page.waitForLoadState('domcontentloaded');
  114 |     const rootHtml = await page.locator('#root').innerHTML();
  115 |     expect(rootHtml.length).toBeGreaterThan(0);
  116 |   });
  117 | 
  118 |   test('Should render and interact with Experiments (pages/Experiments.tsx)', async ({ page }) => {
  119 |     // Mock navigation to route containing Experiments
  120 |     await page.goto(BASE_URL + '/rageval/experiments');
  121 |     await page.waitForLoadState('domcontentloaded');
  122 |     const rootHtml = await page.locator('#root').innerHTML();
  123 |     expect(rootHtml.length).toBeGreaterThan(0);
  124 |   });
  125 | 
  126 |   test('Should render and interact with Traces (pages/Traces.tsx)', async ({ page }) => {
  127 |     // Mock navigation to route containing Traces
  128 |     await page.goto(BASE_URL + '/rageval/traces');
  129 |     await page.waitForLoadState('domcontentloaded');
  130 |     const rootHtml = await page.locator('#root').innerHTML();
  131 |     expect(rootHtml.length).toBeGreaterThan(0);
  132 |   });
  133 | 
  134 |   test('Should render and interact with Overview (pages/Overview.tsx)', async ({ page }) => {
  135 |     // Mock navigation to route containing Overview
  136 |     await page.goto(BASE_URL + '/rageval/overview');
  137 |     await page.waitForLoadState('domcontentloaded');
  138 |     const rootHtml = await page.locator('#root').innerHTML();
  139 |     expect(rootHtml.length).toBeGreaterThan(0);
  140 |   });
  141 | 
  142 |   test('Should render and interact with Models (pages/Models.tsx)', async ({ page }) => {
  143 |     // Mock navigation to route containing Models
  144 |     await page.goto(BASE_URL + '/rageval/models');
  145 |     await page.waitForLoadState('domcontentloaded');
  146 |     const rootHtml = await page.locator('#root').innerHTML();
  147 |     expect(rootHtml.length).toBeGreaterThan(0);
  148 |   });
  149 | 
  150 |   test('Should render and interact with ApiDocs (pages/ApiDocs.tsx)', async ({ page }) => {
  151 |     // Mock navigation to route containing ApiDocs
  152 |     await page.waitForLoadState('domcontentloaded');
> 153 |     const rootHtml = await page.locator('#root').innerHTML();
      |                                                  ^ Error: locator.innerHTML: Test timeout of 45000ms exceeded.
  154 |     expect(rootHtml.length).toBeGreaterThan(0);
  155 |   });
  156 | 
  157 | });
  158 | 
  159 | test.describe("2026 UI/UX Standards Validation", () => {
  160 |   test("Should verify haptic feedback scale animation on buttons", async ({ page }) => {
  161 |     await page.goto(BASE_URL);
  162 |     const btn = page.locator('button').first();
  163 |     if (await btn.isVisible()) {
  164 |       // Hover the button and simulate mouse down to trigger :active
  165 |       const box = await btn.boundingBox();
  166 |       if (box) {
  167 |         await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  168 |         await page.mouse.down();
  169 |         // The scale should drop to 0.96 due to the new CSS rules
  170 |         const transform = await btn.evaluate((el) => window.getComputedStyle(el).transform);
  171 |         // Note: transform is usually a matrix. We check that it's not 'none'.
  172 |         expect(transform).not.toBe('none');
  173 |         await page.mouse.up();
  174 |       }
  175 |     }
  176 |   });
  177 | 
  178 |   test("Should verify accessibility focus-visible rings", async ({ page }) => {
  179 |     await page.goto(BASE_URL);
  180 |     const input = page.locator('input').first();
  181 |     if (await input.isVisible()) {
  182 |       await input.focus();
  183 |       const outline = await input.evaluate((el) => window.getComputedStyle(el).outline);
  184 |       // We expect the focus-visible to trigger either a box-shadow or an outline
  185 |       expect(outline).not.toBe('none');
  186 |     }
  187 |   });
  188 | });
  189 | 
  190 | test.describe("Mobile & Low-Bandwidth Resilience (Sahel Optimized)", () => {
  191 |   test("Should verify strict mobile viewport configuration", async ({ page }) => {
  192 |     await page.goto(BASE_URL);
  193 |     const viewport = await page.locator('meta[name="viewport"]').getAttribute('content');
  194 |     expect(viewport).toContain('width=device-width');
  195 |     expect(viewport).toContain('shrink-to-fit=no');
  196 |     expect(viewport).toContain('maximum-scale=5.0');
  197 |   });
  198 | 
  199 |   test("Should verify offline Service Worker registration", async ({ page }) => {
  200 |     await page.goto(BASE_URL);
  201 |     // Wait for window.onload so SW registers
  202 |     await page.waitForLoadState('domcontentloaded');
  203 |     
  204 |     // Evaluate if a service worker is registered in the navigator
  205 |     const isSwRegistered = await page.evaluate(async () => {
  206 |       if (!('serviceWorker' in navigator)) return false;
  207 |       const registrations = await navigator.serviceWorker.getRegistrations();
  208 |       return registrations.length > 0;
  209 |     });
  210 |     
  211 |     expect(isSwRegistered).toBe(true);
  212 |   });
  213 | 
  214 |   test("Should verify Service Worker uses Network-First strategy for documents to prevent stale cache", async ({ page }) => {
  215 |     // Intercept network requests to verify the SW doesn't block the document fetch
  216 |     let documentFetchedFromNetwork = false;
  217 |     page.on('request', request => {
  218 |       if (request.resourceType() === 'document' && request.url() === '/' + '/') {
  219 |         documentFetchedFromNetwork = true;
  220 |       }
  221 |     });
  222 |     
  223 |     await page.goto(BASE_URL);
  224 |     await page.waitForLoadState('domcontentloaded');
  225 |     
  226 |     // Evaluate the active Service Worker state to ensure it skips waiting
  227 |     const swState = await page.evaluate(async () => {
  228 |       const reg = await navigator.serviceWorker.ready;
  229 |       return reg.active ? reg.active.state : 'none';
  230 |     });
  231 |     
  232 |     expect(['activated', 'activating']).toContain(swState);
  233 |   });
  234 | });
  235 | 
```