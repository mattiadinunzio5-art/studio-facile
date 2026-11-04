/**
 * Test responsive end-to-end con Playwright (Chromium).
 *
 * Prerequisito: backend + frontend in esecuzione (es. scripts/dev.sh o
 * `vite preview`). Uso:
 *   NEXUS_URL=http://127.0.0.1:5173 node scripts/check_responsive.cjs
 *
 * Per ogni pagina e viewport verifica: nessuno scroll orizzontale, nessun
 * errore in console, contenuto principale visibile. Salva screenshot in
 * scripts/out/.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = process.env.NEXUS_URL || 'http://127.0.0.1:5173';
const OUT = path.join(__dirname, 'out');
const VIEWPORTS = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
];
const ROUTES = ['/', '/briefing', '/documents', '/bibliography', '/research', '/history', '/history/events/2', '/time-machine?year=1972', '/graph', '/financial', '/financial/series/1', '/financial/compare', '/war-room', '/war-room/runs/1', '/lab', '/lab/simulations/1', '/studio', '/studio/reports/1', '/projects', '/sources', '/activity', '/notifications', '/settings', '/account', '/search?q=dollaro'];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const failures = [];
  for (const vp of VIEWPORTS) {
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
    const errors = [];
    page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
    page.on('pageerror', (e) => errors.push(e.message));
    for (const route of ROUTES) {
      errors.length = 0;
      await page.goto(BASE + route, { waitUntil: 'networkidle' });
      await page.waitForSelector('main h1', { timeout: 5000 });
      const m = await page.evaluate(() => {
        const main = document.querySelector('main');
        return {
          docOverflow: document.documentElement.scrollWidth - window.innerWidth,
          mainOverflow: main ? main.scrollWidth - main.clientWidth : 0,
          h1: document.querySelector('main h1')?.textContent,
        };
      });
      const tag = `${vp.name} ${route}`;
      if (m.docOverflow > 0) failures.push(`${tag}: overflow orizzontale documento ${m.docOverflow}px`);
      if (m.mainOverflow > 0) failures.push(`${tag}: overflow orizzontale main ${m.mainOverflow}px`);
      if (errors.length) failures.push(`${tag}: errori console: ${errors.join(' | ')}`);
      if (['/', '/financial/series/1', '/time-machine?year=1972', '/graph', '/war-room/runs/1', '/lab/simulations/1', '/studio/reports/1', '/briefing'].includes(route)) {
        await page.screenshot({ path: path.join(OUT, `${vp.name}${route === '/' ? '-dashboard' : route.replace(/[^a-z0-9]+/gi, '-')}.png`), fullPage: true });
      }
      console.log(`ok  ${tag.padEnd(34)} h1="${m.h1}"`);
    }
    if (vp.width < 1024) {
      // Il menu mobile deve aprirsi e mostrare gli 8 moduli.
      await page.goto(BASE + '/', { waitUntil: 'networkidle' });
      await page.click('button[aria-label="Apri menu"]');
      const visible = await page.locator('#nexus-sidebar a[data-module]').evaluateAll((els) =>
        els.filter((e) => { const r = e.getBoundingClientRect(); return r.right > 0 && r.left < window.innerWidth; }).length,
      );
      if (visible !== 8) failures.push(`${vp.name}: menu mobile mostra ${visible}/8 moduli`);
      else console.log(`ok  ${vp.name} menu mobile: 8 moduli visibili`);
      await page.screenshot({ path: path.join(OUT, `${vp.name}-menu.png`) });
    }
    await page.close();
  }
  await browser.close();
  if (failures.length) {
    console.error('\nFALLITO:\n' + failures.join('\n'));
    process.exit(1);
  }
  console.log('\nTest responsive superati.');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
