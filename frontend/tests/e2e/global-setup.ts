import fs from 'fs/promises';
import path from 'path';
import { chromium, type FullConfig } from '@playwright/test';

interface StorageState {
  cookies: unknown[];
  origins: unknown[];
}

const STORAGE_DIR = path.resolve(__dirname, 'storage');
const EMPTY_STORAGE_STATE: StorageState = { cookies: [], origins: [] };

const readNodeEnv = (name: string): string | undefined => {
  const rawValue = process.env[name];
  return typeof rawValue === 'string' && rawValue !== '' ? rawValue : undefined;
};

const writeEmptyState = async (targetPath: string): Promise<void> => {
  await fs.writeFile(targetPath, JSON.stringify(EMPTY_STORAGE_STATE, null, 2));
};

const launchChromiumOrThrow = async () => {
  try {
    return await chromium.launch({ headless: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const missingLibraryPattern =
      message.includes('error while loading shared libraries') ||
      message.includes('libnspr4.so') ||
      message.includes('libnss3.so');

    if (missingLibraryPattern) {
      throw new Error(
        [
          'Playwright browser dependencies are missing on this machine.',
          'Run `pnpm exec playwright install --with-deps chromium` with sudo/root privileges,',
          'or run E2E in CI / Playwright container image.',
          `Original error: ${message}`,
        ].join(' ')
      );
    }

    throw error;
  }
};

const shouldSkipBrowserPreflight = (): boolean =>
  readNodeEnv('E2E_SKIP_BROWSER_PREFLIGHT')?.toLowerCase() === 'true';

const validateBrowserDependencies = async (): Promise<void> => {
  const browser = await launchChromiumOrThrow();
  await browser.close();
};

const globalSetup = async (_config: FullConfig): Promise<void> => {
  await fs.mkdir(STORAGE_DIR, { recursive: true });

  const adminStatePath = path.join(STORAGE_DIR, 'admin-state.json');
  const assetManagerStatePath = path.join(STORAGE_DIR, 'asset-manager-state.json');
  const assetViewerStatePath = path.join(STORAGE_DIR, 'asset-viewer-state.json');

  await Promise.all([
    writeEmptyState(adminStatePath),
    writeEmptyState(assetManagerStatePath),
    writeEmptyState(assetViewerStatePath),
  ]);

  if (!shouldSkipBrowserPreflight()) {
    await validateBrowserDependencies();
  }
};

export default globalSetup;
