/** Capture actual SpendWise screens after a one-time manual sign-in.
 * Run from frontend with: node scripts/capture-screenshots.mjs
 * Both SpendWise servers must already be running.
 */
import { mkdir, writeFile, access } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const output = resolve(root, 'output/screenshots', stamp);
const base = new URL(process.env.SPENDWISE_URL || 'http://localhost:3000');
if (!['localhost', '127.0.0.1', '[::1]'].includes(base.hostname)) {
  throw new Error('This demonstration script only captures a local SpendWise server.');
}
let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch {
  console.error('Install Playwright first: npm install --save-dev playwright');
  process.exit(1);
}
await mkdir(output, { recursive: true });
let browser;
let context;
async function launchBrowser() {
  const candidates = process.env.SPENDWISE_BROWSER_PATH
    ? [{ label: 'Selected browser', options: { executablePath: process.env.SPENDWISE_BROWSER_PATH } }]
    : process.platform === 'win32'
      ? [{ label: 'Microsoft Edge', options: { channel: 'msedge' } },
         { label: 'Playwright Chromium', options: {} }]
      : [{ label: 'Playwright Chromium', options: {} }];
  const errors = [];
  for (const candidate of candidates) {
    try {
      if (candidate.options.executablePath) await access(candidate.options.executablePath);
      console.log(`Opening ${candidate.label}...`);
      const instance = await chromium.launch({
        headless: false,
        timeout: 30000,
        ...candidate.options,
      });
      return instance;
    } catch (error) {
      errors.push(`${candidate.label}: ${error.message.split('\n')[0]}`);
      console.warn(`${candidate.label} could not start. Trying the next available browser.`);
    }
  }
  throw new Error(`No browser could start.\n${errors.join('\n')}\nOn Windows, try Microsoft Edge by setting SPENDWISE_BROWSER_PATH to its msedge.exe path.`);
}
const captured = [];
let page;
async function save(name, options = {}) {
  const path = resolve(output, `${name}.png`);
  await page.screenshot({ path, fullPage: true, animations: 'disabled', ...options });
  captured.push({ name, file: `${name}.png`, url: page.url() });
  console.log(`Saved ${name}.png`);
}

try {
  browser = await launchBrowser();
  context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  deviceScaleFactor: 1.5,
  reducedMotion: 'reduce',
  locale: 'en-IN',
  timezoneId: 'Asia/Kolkata',
});
  page = await context.newPage();
page.setDefaultTimeout(60000);
page.setDefaultNavigationTimeout(60000);
  await page.goto(base.href, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'Welcome back', exact: true }).waitFor();
  await save('01-login');
  console.log('\nSign in to SpendWise in the browser window that just opened.');
  console.log('Use your Umang account. Your password is not stored by this script.');
  console.log('Capture starts automatically after login (up to 5 minutes).\n');
  await page.getByRole('link', { name: 'Overview', exact: true }).waitFor({ timeout: 300000 });

  const screens = [
    ['02-dashboard', '/', '/api/dashboard'],
    ['03-transactions', '/transactions', '/api/transactions'],
    ['04-budgets', '/budgets', '/api/budgets'],
    ['05-subscriptions', '/subscriptions', '/api/subscriptions'],
    ['06-insights', '/insights', '/api/insights'],
    ['07-forecast', '/forecast', '/api/forecast'],
    ['08-reports', '/reports', '/api/reports'],
    ['09-settings', '/settings', '/api/auth/me'],
  ];
  for (const [name, route, endpoint] of screens) {
    const responsePromise = page.waitForResponse(response =>
      new URL(response.url()).pathname === endpoint
      && response.request().method() === 'GET');
    await page.goto(new URL(route, base).href, { waitUntil: 'domcontentloaded' });
    const response = await responsePromise;
    if (!response.ok()) throw new Error(`${name}: API returned HTTP ${response.status()}`);
    await page.getByRole('link', { name: 'Overview', exact: true }).waitFor();
    await page.locator('.animate-pulse').waitFor({ state: 'detached' });
    await page.evaluate(() => document.fonts.ready);
    // Recharts uses JavaScript animation in addition to CSS transitions.
    await page.waitForTimeout(1800);
    await save(name, route === '/settings' ? { mask: [page.locator('input[disabled]')] } : {});
  }
  await writeFile(resolve(output, 'manifest.json'), JSON.stringify({
    capturedAt: new Date().toISOString(),
    source: 'Actual browser captures of the local SpendWise application',
    settingsEmailMasked: true,
    screenshots: captured,
  }, null, 2));
  console.log(`\nDone. ${captured.length} screenshots saved to:\n${output}`);
} catch (error) {
  console.error(`\nCapture stopped: ${error.message}`);
  console.error('Confirm both servers are running and sign in within five minutes.');
  console.error(`Any completed captures are in: ${output}`);
  process.exitCode = 1;
} finally {
  if (context) await context.close();
  if (browser) await browser.close();
}
