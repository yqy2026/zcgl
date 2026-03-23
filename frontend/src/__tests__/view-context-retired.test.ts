import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const currentFilePath = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFilePath);
const srcDir = path.resolve(currentDir, '..');

describe('View context retirement', () => {
  it('removes the obsolete runtime view context files', () => {
    expect(fs.existsSync(path.join(srcDir, 'contexts', 'ViewContext.tsx'))).toBe(false);
    expect(fs.existsSync(path.join(srcDir, 'utils', 'viewSelectionStorage.ts'))).toBe(false);
    expect(fs.existsSync(path.join(srcDir, 'types', 'viewSelection.ts'))).toBe(false);
  });
});
