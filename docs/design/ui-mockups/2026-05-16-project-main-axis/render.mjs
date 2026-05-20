import { access, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const currentDir = dirname(fileURLToPath(import.meta.url));
const requireFromFrontend = createRequire(resolve(currentDir, '../../../../frontend/package.json'));
const { chromium } = requireFromFrontend('playwright');
const sourcePath = resolve(currentDir, 'source.html');
const outputDir = resolve(currentDir, 'png');

const screens = [
  ['dashboard', 'ui-01-dashboard.png'],
  ['project-detail', 'ui-02-project-detail.png'],
  ['contract-relation', 'ui-03-contract-relation.png'],
  ['analytics-ledger', 'ui-04-analytics-ledger.png'],
];

const browserCandidates = [
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean);

async function findExecutablePath() {
  for (const candidate of browserCandidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // Keep trying the next installed browser path.
    }
  }

  return undefined;
}

await mkdir(outputDir, { recursive: true });

const executablePath = await findExecutablePath();
const browser = await chromium.launch(executablePath != null ? { executablePath } : {});
const page = await browser.newPage({
  viewport: { width: 1504, height: 1024 },
  deviceScaleFactor: 1,
});

await page.goto(pathToFileURL(sourcePath).href);

for (const [id, filename] of screens) {
  const locator = page.locator(`#${id}`);
  await locator.screenshot({
    path: resolve(outputDir, filename),
    animations: 'disabled',
  });
}

await browser.close();
