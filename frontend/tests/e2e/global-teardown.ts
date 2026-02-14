import fs from 'fs/promises';
import path from 'path';
import { type FullConfig } from '@playwright/test';

const STORAGE_DIR = path.resolve(__dirname, 'storage');
const readNodeEnv = (name: string): string | undefined => {
  const rawValue = process.env[name];
  return typeof rawValue === 'string' && rawValue !== '' ? rawValue : undefined;
};

const shouldCleanupStorageState = (): boolean => {
  const value = readNodeEnv('E2E_CLEANUP_STORAGE_STATE');
  return value != null && value.toLowerCase() === 'true';
};

const globalTeardown = async (_config: FullConfig): Promise<void> => {
  if (!shouldCleanupStorageState()) {
    return;
  }

  const filesToDelete = [
    'admin-state.json',
    'asset-manager-state.json',
    'asset-viewer-state.json',
  ].map(fileName => path.join(STORAGE_DIR, fileName));

  await Promise.all(
    filesToDelete.map(async filePath => {
      try {
        await fs.unlink(filePath);
      } catch {
        // 忽略不存在文件
      }
    })
  );
};

export default globalTeardown;
