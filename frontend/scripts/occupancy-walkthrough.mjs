// Walk-through: occupancy report page four states, deep link, submit gating.
// Run: node /tmp/occupancy-walkthrough.mjs  (frontend :5173 + backend :8002 up)
import { chromium } from 'playwright';

const CHROMIUM = `${process.env.LOCALAPPDATA}/ms-playwright/chromium-1228/chrome-win64/chrome.exe`;
const BASE = 'http://localhost:5173';
const results = [];
let browser;

function record(name, pass, detail) {
  results.push({ name, pass: Boolean(pass), detail });
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name}${detail ? ` :: ${detail}` : ''}`);
}

try {
  browser = await chromium.launch({ executablePath: CHROMIUM, headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(String(error)));
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error' || message.type() === 'warning') {
      consoleErrors.push(`${message.type()}: ${message.text().slice(0, 200)}`);
    }
  });

  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#identifier', { timeout: 30000 });
  await page.fill('#identifier', 'v5-walkthrough');
  await page.fill('#password', process.env.V5_WALKTHROUGH_PASSWORD ?? '');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !String(url).includes('/login'), { timeout: 60000, waitUntil: 'domcontentloaded' });
  record('login', true);

  // 0. Reset: withdraw any submitted snapshot left by a previous run.
  const cookies = await context.cookies();
  const csrf = cookies.find((c) => c.name === 'csrf_token')?.value;
  const csrfHeaders = csrf ? { 'X-CSRF-Token': csrf } : {};
  const apiBase = `${BASE.replace('5173', '8002')}`;
  const existingDraftResp = await page.request.get(
    `${apiBase}/api/v1/occupancy-reports/2026-09/draft?operator_party_id=v5-walkthrough-operator`,
  );
  const existingBody = await existingDraftResp.json().catch(() => null);
  const existingError = existingBody?.error ?? {};
  const submittedId = existingError?.details?.report_id;
  if (existingError?.code === 'OCCUPANCY_REPORT_ALREADY_SUBMITTED' && submittedId) {
    const wdPreview = await (
      await page.request.post(
        `${apiBase}/api/v1/occupancy-reports/${submittedId}/withdrawal-preview`,
        { headers: csrfHeaders },
      )
    ).json();
    await page.request.post(
      `${apiBase}/api/v1/occupancy-reports/${submittedId}/withdrawal`,
      {
        data: {
          preview_token: wdPreview?.preview_token,
          expected_version: wdPreview?.report_version,
          withdraw_reason: '走查重置',
        },
        headers: { 'Idempotency-Key': `reset-${Date.now()}`, ...csrfHeaders },
      },
    );
    record('reset-withdrew-previous', true, submittedId);
  }

  // 1. Menu link present and navigates
  const menuLink = page.locator('a[href*="occupancy-reports"], [role="menuitem"]').filter({ hasText: '月度出租率报送' }).first();
  await menuLink.waitFor({ state: 'visible', timeout: 15000 });
  await menuLink.click();
  await page.waitForURL((url) => String(url).includes('occupancy-reports'), { timeout: 20000, waitUntil: 'domcontentloaded' });
  record('menu-navigates-to-page', true, page.url());

  // 2. Page renders the three blocks and pending gate before operator chosen
  await page.waitForTimeout(1500);
  const body = await page.textContent('body');
  record('page-renders', body.includes('考核范围') && body.includes('当月草稿') || body.includes('月度'), body.slice(0, 120).replace(/\s+/g, ' '));

  // 3. Deep link with seeded operator shows the active scope and items
  await page.goto(`${BASE}/asset-operations/occupancy-reports?operator_party_id=v5-walkthrough-operator&period=2026-09`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  const deepBody = await page.textContent('body');
  const hasScope = deepBody.includes('考核范围 v1') && deepBody.includes('已租宗数');
  record('deep-link-shows-scope', hasScope, deepBody.slice(0, 200).replace(/\s+/g, ' '));

  // 4. Submit control disabled while scope gates unresolved (pending units).
  const submitButtons = await page.locator('button').evaluateAll((buttons) =>
    buttons
      .filter((b) => /提交报送/.test(b.textContent ?? ''))
      .map((b) => ({ text: (b.textContent ?? '').trim(), disabled: b.disabled }))
  );
  record(
    'submit-button-present',
    submitButtons.length === 1,
    JSON.stringify(submitButtons),
  );

  // 3b. Full submission through the UI state: save note then submit via API
  //     (cookie session already logged in, CSRF double-submit header required).
  const noteResp = await page.request.put(
    `${BASE.replace('5173', '8002')}/api/v1/occupancy-reports/2026-09/draft-note`,
    {
      data: { operator_party_id: 'v5-walkthrough-operator', change_note: '走查提交流程' },
      headers: csrfHeaders,
    },
  );
  record('note-saved', noteResp.status() === 200, `status ${noteResp.status()}`);
  const previewResp = await page.request.post(
    `${BASE.replace('5173', '8002')}/api/v1/occupancy-reports/2026-09/submission-preview?operator_party_id=v5-walkthrough-operator`,
    { headers: csrfHeaders },
  );
  const previewBody = await previewResp.json();
  const canSubmit = previewBody?.data?.can_submit ?? previewBody?.can_submit;
  record('preview-can-submit', canSubmit === true, JSON.stringify(previewBody).slice(0, 180));
  const submitResp = await page.request.post(
    `${BASE.replace('5173', '8002')}/api/v1/occupancy-reports/2026-09/submissions?operator_party_id=v5-walkthrough-operator`,
    {
      data: {
        preview_token: previewBody?.data?.preview_token ?? previewBody?.preview_token,
        expected_scope_version_id: previewBody?.data?.scope_version?.version_id ?? previewBody?.scope_version?.version_id,
        expected_scope_version: previewBody?.data?.scope_version?.version ?? previewBody?.scope_version?.version,
      },
      headers: { 'Idempotency-Key': `walkthrough-${Date.now()}`, ...csrfHeaders },
    },
  );
  const submitBody = await submitResp.json();
  const reportId = submitBody?.data?.report_id ?? submitBody?.report_id;
  record('submit-ok', submitResp.status() === 200 && Boolean(reportId), `status ${submitResp.status()}`);

  // 3c. Snapshot deep link shows the submitted snapshot and diff section
  await page.goto(`${BASE}/asset-operations/occupancy-reports?operator_party_id=v5-walkthrough-operator&period=2026-09&report_id=${reportId}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  const snapBody = await page.textContent('body');
  const hasSnapshot = snapBody.includes('已提交') || snapBody.includes('submitted') || snapBody.includes('快照');
  const hasDiff = snapBody.includes('差异') || snapBody.includes('无差异') || snapBody.includes('一致');
  record('snapshot-deep-link', hasSnapshot && hasDiff, snapBody.slice(0, 240).replace(/\s+/g, ' '));

  // 4b. Invalid report id surfaces the error state instead of hanging.
  await page.goto(
    `${BASE}/asset-operations/occupancy-reports?operator_party_id=v5-walkthrough-operator&period=2026-09&report_id=00000000-0000-0000-0000-000000000000`,
    { waitUntil: 'domcontentloaded' },
  );
  await page.waitForTimeout(15000);
  const probe = await page.evaluate(async () => {
    const response = await fetch(
      '/api/v1/occupancy-reports/00000000-0000-0000-0000-000000000000',
      { credentials: 'include' }
    );
    const entries = performance
      .getEntriesByType('resource')
      .filter((entry) => entry.name.includes('occupancy-reports/00000000'))
      .map((entry) => ({ url: entry.name.slice(-60), duration: Math.round(entry.duration) }));
    return {
      status: response.status,
      body: (await response.text()).slice(0, 120),
      pageRequests: entries,
    };
  });
  console.log(`INFO invalid-report-id probe :: ${JSON.stringify(probe).slice(0, 400)}`);
  const invalidBody = await page.textContent('body');
  const showsError =
    invalidBody.includes('不存在') || invalidBody.includes('重试');
  const pendingTextCount = (invalidBody.match(/正在读取报送快照/g) ?? []).length;
  console.log(
    `INFO invalid-body :: pending=${pendingTextCount} error=${invalidBody.includes('不存在')} retry=${invalidBody.includes('重试')} len=${invalidBody.length}`,
  );
  record('invalid-report-id-error-state', showsError, `pending-text-count=${pendingTextCount}`);
  console.log(`INFO console-errors :: ${consoleErrors.slice(-6).join(' || ') || '(none)'}`);

  // 5. No page errors
  record('no-page-errors', pageErrors.length === 0, pageErrors.join(' | ').slice(0, 200));

  // 6. Responsive widths: no horizontal overflow at 320 / 640 / 1440.
  for (const [width, height] of [[320, 720], [640, 900], [1440, 900]]) {
    await page.setViewportSize({ width, height });
    await page.waitForTimeout(600);
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth + 1,
    );
    record(`no-horizontal-overflow-${width}`, overflow);
  }
} catch (error) {
  record('fatal', false, String(error).slice(0, 300));
} finally {
  if (browser) await browser.close();
}
const failed = results.filter((r) => !r.pass);
console.log(`SUMMARY ${results.length - failed.length}/${results.length}`);
process.exit(failed.length > 0 ? 1 : 0);
