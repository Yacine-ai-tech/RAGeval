# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: exhaustive_ui.spec.ts >> Mobile & Low-Bandwidth Resilience (Sahel Optimized) >> Should verify Service Worker uses Network-First strategy for documents to prevent stale cache
- Location: e2e/exhaustive_ui.spec.ts:214:3

# Error details

```
Test timeout of 45000ms exceeded.
```

```
Error: page.evaluate: Test timeout of 45000ms exceeded.
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e5]:
    - generic [ref=e7]:
      - generic [ref=e8]: RAGeval
      - generic [ref=e9]: LLMOps Observability
    - navigation [ref=e10]:
      - link "Overview" [ref=e11] [cursor=pointer]:
        - /url: /
        - img [ref=e13]
        - text: Overview
      - link "Queries" [ref=e16] [cursor=pointer]:
        - /url: /queries
        - img [ref=e17]
        - text: Queries
      - link "Live Traces" [ref=e20] [cursor=pointer]:
        - /url: /traces
        - img [ref=e21]
        - text: Live Traces
      - link "Evaluate" [ref=e28] [cursor=pointer]:
        - /url: /evaluate
        - img [ref=e29]
        - text: Evaluate
      - link "Experiments" [ref=e31] [cursor=pointer]:
        - /url: /experiments
        - img [ref=e32]
        - text: Experiments
      - link "Saved" [ref=e34] [cursor=pointer]:
        - /url: /saved
        - img [ref=e35]
        - text: Saved
      - link "Models" [ref=e37] [cursor=pointer]:
        - /url: /models
        - img [ref=e38]
        - text: Models
      - link "Cost" [ref=e48] [cursor=pointer]:
        - /url: /cost
        - img [ref=e49]
        - text: Cost
      - link "Alerts" [ref=e52] [cursor=pointer]:
        - /url: /alerts
        - img [ref=e53]
        - text: Alerts
      - link "Instrumentation" [ref=e58] [cursor=pointer]:
        - /url: /instrumentation
        - img [ref=e59]
        - text: Instrumentation
      - link "API Docs" [ref=e63] [cursor=pointer]:
        - /url: /api-docs
        - img [ref=e64]
        - text: API Docs
      - link "User Guide" [ref=e68] [cursor=pointer]:
        - /url: /user-guide
        - img [ref=e69]
        - text: User Guide
    - generic [ref=e71]: Backend online
  - main [ref=e74]:
    - generic [ref=e76]:
      - generic [ref=e77]:
        - generic [ref=e78]:
          - heading "Overview" [level=1] [ref=e79]
          - paragraph [ref=e80]: Quality, cost and reliability of every tracked RAG interaction, scored by the multi-judge evaluation pipeline.
        - combobox [ref=e82]:
          - option "Last 7 days" [selected]
          - option "Last 30 days"
          - option "Last 90 days"
      - generic [ref=e83]:
        - generic [ref=e84]:
          - generic [ref=e85]:
            - generic [ref=e86]: Tracked queries
            - img [ref=e87]
          - generic [ref=e91]: "0"
          - generic [ref=e93]: last 7 days
        - generic [ref=e94]:
          - generic [ref=e95]:
            - generic [ref=e96]: Avg retrieval relevance
            - img [ref=e97]
          - generic [ref=e101]: "0.00"
          - generic [ref=e103]: below threshold
        - generic [ref=e104]:
          - generic [ref=e105]:
            - generic [ref=e106]: Avg groundedness
            - img [ref=e107]
          - generic [ref=e110]: "0.00"
          - generic [ref=e112]: review
        - generic [ref=e113]:
          - generic [ref=e114]:
            - generic [ref=e115]: Flagged for review
            - img [ref=e116]
          - generic [ref=e118]: "0"
          - generic [ref=e120]: all clear
      - generic [ref=e121]:
        - generic [ref=e122]:
          - generic [ref=e123]:
            - generic [ref=e124]: Avg faithfulness
            - img [ref=e125]
          - generic [ref=e127]: "0.00"
        - generic [ref=e128]:
          - generic [ref=e129]:
            - generic [ref=e130]: Avg latency
            - img [ref=e131]
          - generic [ref=e134]: 0 ms
        - generic [ref=e135]:
          - generic [ref=e136]:
            - generic [ref=e137]: Total cost
            - img [ref=e138]
          - generic [ref=e141]: $0.0000
          - generic [ref=e143]: last 7 days
      - generic [ref=e144]:
        - generic [ref=e145]:
          - generic [ref=e146]: Quality per tracked query
          - generic "derived client-side from the real query log" [ref=e148]: query log
        - generic [ref=e150]:
          - img [ref=e151]
          - generic [ref=e154]: No tracked interactions yet
          - generic [ref=e155]: Score one on the Evaluate page or instrument your RAG app with the @track decorator.
          - link "Open Evaluate" [ref=e157] [cursor=pointer]:
            - /url: /evaluate
            - text: Open Evaluate
            - img [ref=e158]
```

# Test source

```ts
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
  153 |     const rootHtml = await page.locator('#root').innerHTML();
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
> 227 |     const swState = await page.evaluate(async () => {
      |                                ^ Error: page.evaluate: Test timeout of 45000ms exceeded.
  228 |       const reg = await navigator.serviceWorker.ready;
  229 |       return reg.active ? reg.active.state : 'none';
  230 |     });
  231 |     
  232 |     expect(['activated', 'activating']).toContain(swState);
  233 |   });
  234 | });
  235 | 
```