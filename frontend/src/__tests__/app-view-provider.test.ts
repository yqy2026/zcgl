import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const currentFilePath = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFilePath);
const appFilePath = path.resolve(currentDir, '../App.tsx');

const readAppSource = (): string => fs.readFileSync(appFilePath, 'utf8');

describe('App ViewProvider wiring', () => {
  it('should not import ViewProvider once route-derived perspective is in use', () => {
    const source = readAppSource();

    expect(source).not.toContain("import { ViewProvider } from './contexts/ViewContext';");
  });

  it('should nest AntdApp directly under AuthProvider', () => {
    const source = readAppSource();

    expect(source).toMatch(/<AuthProvider>\s*<AntdApp>/s);
    expect(source).toMatch(/<\/AntdApp>\s*<\/AuthProvider>/s);
    expect(source).not.toContain('<ViewProvider>');
  });
});
