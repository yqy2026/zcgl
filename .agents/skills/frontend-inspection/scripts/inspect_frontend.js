#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const DEFAULT_ROUTES = [
  '/dashboard',
  '/assets/list',
  '/assets/new',
  '/assets/import',
  '/assets/analytics',
  '/assets/analytics-simple',
  '/rental/contracts',
  '/rental/contracts/new',
  '/rental/contracts/pdf-import',
  '/rental/ledger',
  '/rental/statistics',
  '/property-certificates',
  '/property-certificates/import',
  '/ownership',
  '/project',
  '/profile',
  '/system/users',
  '/system/roles',
  '/system/organizations',
  '/system/dictionaries',
  '/system/templates',
  '/system/logs',
  '/system/settings',
];

function printHelp() {
  console.log(`Frontend inspection runner

Usage:
  node .agents/skills/frontend-inspection/scripts/inspect_frontend.js [options]

Options:
  --base-url <url>         Frontend base URL (default: http://127.0.0.1:5173)
  --username <value>       Login username (default: admin)
  --password <value>       Login password (default: admin123)
  --chromium-path <path>   Chromium executable path
  --out-dir <path>         Output directory
  --routes-file <path>     Route list file (one route per line)
  --route <path>           Add one route (repeatable)
  --wait-ms <number>       Extra wait after navigation (default: 800)
  --full-page              Capture full-page screenshots
  --help                   Show this help

Examples:
  node .agents/skills/frontend-inspection/scripts/inspect_frontend.js
  node .agents/skills/frontend-inspection/scripts/inspect_frontend.js --route /dashboard --route /system/users
  node .agents/skills/frontend-inspection/scripts/inspect_frontend.js --routes-file ./routes.txt
`);
}

function parseArgs(argv) {
  const options = {
    baseUrl: 'http://127.0.0.1:5173',
    username: process.env.INSPECT_USERNAME || 'admin',
    password: process.env.INSPECT_PASSWORD || 'admin123',
    chromiumPath: process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser',
    outDir: null,
    routesFile: null,
    routes: [],
    waitMs: 800,
    fullPage: false,
    help: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    if (arg === '--help') {
      options.help = true;
      continue;
    }
    if (arg === '--full-page') {
      options.fullPage = true;
      continue;
    }

    const value = argv[i + 1];
    const needsValue = [
      '--base-url',
      '--username',
      '--password',
      '--chromium-path',
      '--out-dir',
      '--routes-file',
      '--route',
      '--wait-ms',
    ].includes(arg);

    if (needsValue && (value == null || value.startsWith('--'))) {
      throw new Error(`Missing value for ${arg}`);
    }

    switch (arg) {
      case '--base-url':
        options.baseUrl = value;
        i += 1;
        break;
      case '--username':
        options.username = value;
        i += 1;
        break;
      case '--password':
        options.password = value;
        i += 1;
        break;
      case '--chromium-path':
        options.chromiumPath = value;
        i += 1;
        break;
      case '--out-dir':
        options.outDir = value;
        i += 1;
        break;
      case '--routes-file':
        options.routesFile = value;
        i += 1;
        break;
      case '--route':
        options.routes.push(value);
        i += 1;
        break;
      case '--wait-ms': {
        const parsed = Number.parseInt(value, 10);
        if (!Number.isFinite(parsed) || parsed < 0) {
          throw new Error(`Invalid --wait-ms value: ${value}`);
        }
        options.waitMs = parsed;
        i += 1;
        break;
      }
      default:
        throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return options;
}

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function shouldIgnoreHttpError(url) {
  return url.includes('.map') || url.includes('source-map') || url.includes('favicon.ico');
}

function shouldIgnoreRequestFailure(failureText) {
  const normalized = typeof failureText === 'string' ? failureText.trim() : '';
  return normalized === 'net::ERR_ABORTED';
}

function dedupeRoutes(routes) {
  const seen = new Set();
  const result = [];

  for (const route of routes) {
    const normalized = route.trim();
    if (normalized === '') {
      continue;
    }
    const withSlash = normalized.startsWith('/') ? normalized : `/${normalized}`;
    if (!seen.has(withSlash)) {
      seen.add(withSlash);
      result.push(withSlash);
    }
  }

  return result;
}

function loadRoutes(options) {
  if (options.routes.length > 0) {
    return dedupeRoutes(options.routes);
  }

  if (options.routesFile != null) {
    const filePath = path.isAbsolute(options.routesFile)
      ? options.routesFile
      : path.resolve(process.cwd(), options.routesFile);

    if (!fs.existsSync(filePath)) {
      throw new Error(`Routes file not found: ${filePath}`);
    }

    const text = fs.readFileSync(filePath, 'utf8');
    const lines = text
      .split('\n')
      .map(line => line.trim())
      .filter(line => line !== '' && !line.startsWith('#'));

    return dedupeRoutes(lines);
  }

  return [...DEFAULT_ROUTES];
}

function resolveRepoRoot() {
  return path.resolve(__dirname, '../../../../');
}

function loadPlaywright(repoRoot) {
  const localModulePath = path.join(repoRoot, 'frontend', 'node_modules', 'playwright');
  const candidates = [localModulePath, 'playwright'];

  for (const candidate of candidates) {
    try {
      // eslint-disable-next-line global-require, import/no-dynamic-require
      return require(candidate);
    } catch {
      // continue
    }
  }

  throw new Error(
    'Cannot load Playwright. Run `corepack pnpm --dir frontend install` first.'
  );
}

async function waitStable(page, waitMs) {
  await page.waitForTimeout(waitMs);
  try {
    await page.waitForLoadState('networkidle', { timeout: 8000 });
  } catch {
    // Some pages poll continuously.
  }
  await page.waitForTimeout(250);
}

async function login(page, options) {
  await page.goto(`${options.baseUrl}/login`, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  await waitStable(page, options.waitMs);

  const usernameInput = page
    .locator('input#identifier, input[name="identifier"], input#login_username, input[name="username"]')
    .first();
  const passwordInput = page
    .locator('input#password, input[name="password"], input#login_password')
    .first();
  const submitButton = page.locator('button[type="submit"]').first();

  await usernameInput.waitFor({ state: 'visible', timeout: 15000 });
  await passwordInput.waitFor({ state: 'visible', timeout: 15000 });
  await submitButton.waitFor({ state: 'visible', timeout: 15000 });

  await usernameInput.fill(options.username);
  await passwordInput.fill(options.password);
  await submitButton.click();

  await page.waitForURL(url => !url.pathname.startsWith('/login'), { timeout: 15000 });
  await waitStable(page, options.waitMs);

  const authStatus = await page.evaluate(async () => {
    try {
      const response = await fetch('/api/v1/auth/me', { credentials: 'include' });
      return response.status;
    } catch {
      return 0;
    }
  });

  if (authStatus !== 200) {
    throw new Error(`/api/v1/auth/me returned ${authStatus}`);
  }
}

async function inspectOneRoute(page, route, options, screenshotDir) {
  const consoleIssues = [];
  const failedRequests = [];
  const ignoredFailedRequests = [];
  const httpErrors = [];

  const onConsole = msg => {
    const type = msg.type();
    if (type === 'error' || type === 'warning') {
      const text = msg.text();
      if (text.includes('download the React DevTools')) {
        return;
      }
      consoleIssues.push({ type, text: text.slice(0, 500) });
    }
  };

  const onRequestFailed = request => {
    const failure = request.failure()?.errorText || 'unknown';
    const failedRequest = {
      method: request.method(),
      url: request.url().slice(0, 500),
      failure,
    };

    if (shouldIgnoreRequestFailure(failure)) {
      ignoredFailedRequests.push(failedRequest);
      return;
    }

    failedRequests.push(failedRequest);
  };

  const onResponse = response => {
    const status = response.status();
    const url = response.url();
    if (status >= 400 && !shouldIgnoreHttpError(url)) {
      httpErrors.push({ status, url: url.slice(0, 500) });
    }
  };

  page.on('console', onConsole);
  page.on('requestfailed', onRequestFailed);
  page.on('response', onResponse);

  let navError = null;
  try {
    await page.goto(`${options.baseUrl}${route}`, {
      waitUntil: 'domcontentloaded',
      timeout: 25000,
    });
    await waitStable(page, options.waitMs);
  } catch (error) {
    navError = error instanceof Error ? error.message : String(error);
  }

  page.off('console', onConsole);
  page.off('requestfailed', onRequestFailed);
  page.off('response', onResponse);

  const finalPath = new URL(page.url()).pathname;

  const pageSignals = await page.evaluate(() => {
    const bodyText = document.body?.innerText ?? '';
    const lower = bodyText.toLowerCase();

    return {
      title: document.title,
      has403Word: bodyText.includes('403') || bodyText.includes('无权限') || bodyText.includes('Access Denied'),
      hasUiErrorWord:
        lower.includes('页面加载失败') ||
        lower.includes('something went wrong') ||
        lower.includes('network error') ||
        lower.includes('操作失败'),
      hasMainUi:
        document.querySelector('.ant-layout-content') != null ||
        document.querySelector('.ant-table') != null ||
        document.querySelector('.ant-card') != null ||
        document.querySelector('.ant-form') != null,
    };
  });

  const shotName = `${route.replace(/[^a-zA-Z0-9-]/g, '_') || 'root'}.png`;
  const screenshotPath = path.join(screenshotDir, shotName);
  await page.screenshot({ path: screenshotPath, fullPage: options.fullPage });

  const redirectedToLogin = finalPath.startsWith('/login');
  const forbidden = finalPath.startsWith('/403') || pageSignals.has403Word;

  let status = 'ok';
  if (navError != null || redirectedToLogin || forbidden) {
    status = 'fail';
  } else if (
    pageSignals.hasUiErrorWord ||
    consoleIssues.length > 0 ||
    failedRequests.length > 0 ||
    httpErrors.length > 0
  ) {
    status = 'warn';
  }

  return {
    route,
    status,
    finalPath,
    title: pageSignals.title,
    navError,
    redirectedToLogin,
    forbidden,
    hasUiErrorHint: pageSignals.hasUiErrorWord,
    hasMainUi: pageSignals.hasMainUi,
    consoleIssues,
    failedRequests,
    ignoredFailedRequests,
    httpErrors,
    screenshotPath,
    checkedAt: new Date().toISOString(),
  };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }

  const repoRoot = resolveRepoRoot();
  const playwright = loadPlaywright(repoRoot);
  const routes = loadRoutes(options);

  const outputRoot =
    options.outDir == null
      ? path.join(repoRoot, 'output', 'playwright', `frontend-inspection-${timestamp()}`)
      : path.isAbsolute(options.outDir)
      ? options.outDir
      : path.resolve(process.cwd(), options.outDir);

  fs.mkdirSync(outputRoot, { recursive: true });

  const reportPath = path.join(outputRoot, 'report.json');
  const report = {
    startedAt: new Date().toISOString(),
    config: {
      baseUrl: options.baseUrl,
      username: options.username,
      chromiumPath: options.chromiumPath,
      waitMs: options.waitMs,
      fullPage: options.fullPage,
      routeCount: routes.length,
    },
    login: { ok: false, error: null },
    summary: { total: routes.length, ok: 0, warn: 0, fail: 0 },
    routes: [],
  };

  const writeReport = () => {
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  };

  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: options.chromiumPath,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  const context = await browser.newContext({
    baseURL: options.baseUrl,
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();

  try {
    await login(page, options);
    report.login.ok = true;
  } catch (error) {
    report.login.ok = false;
    report.login.error = error instanceof Error ? error.message : String(error);
    writeReport();
    await browser.close();

    console.error('[FAIL] Login check failed');
    console.error(`report: ${reportPath}`);
    process.exit(2);
  }

  writeReport();

  for (const route of routes) {
    const result = await inspectOneRoute(page, route, options, outputRoot);
    report.routes.push(result);
    report.summary[result.status] += 1;
    writeReport();
    console.log(`[${result.status.toUpperCase()}] ${route} -> ${result.finalPath}`);
  }

  report.finishedAt = new Date().toISOString();
  writeReport();

  await browser.close();

  console.log('\nInspection completed');
  console.log(`output: ${outputRoot}`);
  console.log(`report: ${reportPath}`);
  console.log(
    `summary: total=${report.summary.total}, ok=${report.summary.ok}, warn=${report.summary.warn}, fail=${report.summary.fail}`
  );
}

main().catch(error => {
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
