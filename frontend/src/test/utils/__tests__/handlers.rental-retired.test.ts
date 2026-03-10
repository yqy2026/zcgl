import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const readHandlersSource = (): string => {
  return readFileSync(resolve(process.cwd(), 'src/test/utils/handlers.ts'), 'utf8');
};

describe('test handlers rental retirement', () => {
  it('retires legacy rental contract MSW handlers', () => {
    const source = readHandlersSource();

    expect(source).not.toContain('export const rentContractHandlers');
    expect(source).not.toContain('/rental-contracts/contracts');
    expect(source).not.toContain('...rentContractHandlers');
  });
});
