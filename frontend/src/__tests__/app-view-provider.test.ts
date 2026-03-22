import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const currentFilePath = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFilePath);
const appFilePath = path.resolve(currentDir, '../App.tsx');

const readAppSource = (): string => fs.readFileSync(appFilePath, 'utf8');

describe('App ViewProvider wiring', () => {
  it('should import ViewProvider for runtime useView consumers', () => {
    const source = readAppSource();

    expect(source).toContain("import { ViewProvider } from './contexts/ViewContext';");
  });

  it('should nest ViewProvider between AuthProvider and AntdApp', () => {
    const source = readAppSource();

    expect(source).toMatch(/<AuthProvider>\s*<ViewProvider>\s*<AntdApp>/s);
    expect(source).toMatch(/<\/AntdApp>\s*<\/ViewProvider>\s*<\/AuthProvider>/s);
  });
});
