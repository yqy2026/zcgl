// Walk-through: four v5 pages at default / 200% / 320px, programmatic asserts.
// Run: node scripts/v5-walkthrough.mjs  (frontend dev on :5173 must be up)
import { chromium } from 'playwright';

const CHROMIUM = `${process.env.LOCALAPPDATA}/ms-playwright/chromium-1228/chrome-win64/chrome.exe`;
const BASE = 'http://localhost:5173';
const ROUTES = [
  ['/asset-operations/units', '资产单元'],
  ['/asset-operations/contracts/upstream', '上游合同'],
  ['/asset-operations/contracts/terminal', '终端合同'],
  ['/asset-operations/contracts/intake', '录入已签合同'],
];
const results = [];
let browser;

function record(name, pass, detail) {
  results.push({ name, pass: Boolean(pass), detail });
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name}${detail ? ` :: ${detail}` : ''}`);
}

async function noHorizontalOverflow(page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  );
}

try {
  browser = await chromium.launch({
    executablePath: CHROMIUM,
    headless: true,
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(String(error)));

  // Login
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#identifier', { timeout: 30000 });
  await page.fill('#identifier', 'v5-walkthrough');
  await page.fill('#password', process.env.V5_WALKTHROUGH_PASSWORD ?? '');
  await page.click('button[type="submit"]');
  try {
    await page.waitForURL((url) => !String(url).includes('/login'), { timeout: 60000, waitUntil: 'domcontentloaded' });
    record('login', true);
  // v5 切换断言：登录落点与无旧菜单
  await page.waitForTimeout(400);
  record(
    'post-login lands on units',
    page.url().includes('/asset-operations/units'),
    page.url(),
  );
  const sidebarText = await page
    .locator('aside, .ant-layout-sider')
    .first()
    .innerText()
    .catch(() => '');
  record(
    'sidebar has no legacy entries',
    !sidebarText.includes('工作台') &&
      !sidebarText.includes('资产台账') &&
      !sidebarText.includes('合同中心'),
  );
  record(
    'sidebar has v5 entries',
    sidebarText.includes('资产运营') && sidebarText.includes('资产单元'),
  );
  } catch (error) {
    record('login', false, String(error).slice(0, 120));
    throw error;
  }

  for (const [route, heading] of ROUTES) {
    await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(1200);

    // Default 1280: heading visible
    const headingVisible = await page
      .getByRole('heading', { name: heading })
      .first()
      .isVisible();
    record(`${route} @1280 heading`, headingVisible);

    // 200% via CDP page scale
    const cdp = await context.newCDPSession(page);
    await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 2 });
    await page.waitForTimeout(300);
    const primaryAt200 = await page.evaluate(() => {
      const table = document.querySelector('.ant-table');
      const el = table ?? document.body;
      const rect = el.getBoundingClientRect();
      return rect.left >= -2 && rect.width > 0;
    });
    record(`${route} @200% primary visible`, primaryAt200);
    await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 1 });

    // 320px reflow: no horizontal overflow
    await page.setViewportSize({ width: 320, height: 700 });
    await page.waitForTimeout(400);
    const noOverflow320 = await noHorizontalOverflow(page);
    record(`${route} @320 no h-overflow`, noOverflow320);
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.waitForTimeout(300);
  }

  // Units page: row click opens detail pane
  await page.goto(`${BASE}/asset-operations/units`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(1200);
  const firstRow = page.locator('.ant-table-tbody tr.ant-table-row').first();
  await firstRow.waitFor({ state: 'visible', timeout: 8000 }).catch(() => {});
  if (await firstRow.isVisible()) {
    await firstRow.click();
    await page.waitForTimeout(1500);
    const detailText = await page
      .locator('aside[aria-label="资产单元详情"]')
      .innerText()
      .catch((error) => `aside-error: ${String(error).slice(0, 80)}`);
    record(
      'units detail pane shows contract',
      detailText.includes('AU-WALK') || detailText.includes('TM-WALK'),
      detailText.slice(0, 60),
    );
  } else {
    record('units detail pane shows contract', false, 'no rows');
  }

  record('zero pageerror', pageErrors.length === 0, pageErrors.join('; ').slice(0, 120));
} catch (error) {
  record('walkthrough-script', false, String(error).slice(0, 200));
} finally {
  if (browser != null) {
    await browser.close();
  }
  const failed = results.filter((item) => !item.pass);
  console.log(`\n== ${results.length - failed.length}/${results.length} PASS ==`);
  process.exit(failed.length === 0 ? 0 : 1);
}
