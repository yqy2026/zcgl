import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const readSource = (relativePath: string): string =>
  readFileSync(resolve(process.cwd(), relativePath), 'utf8');

describe('frontend legacy contract e2e hygiene', () => {
  it('stores the import success e2e spec under the legacy-contract directory', () => {
    expect(existsSync(resolve(process.cwd(), 'tests/e2e/legacy-contract/import-success.spec.ts'))).toBe(
      true
    );
    expect(existsSync(resolve(process.cwd(), 'tests/e2e/rental/import-success.spec.ts'))).toBe(false);
  });

  it('retires the stale rental contract workflow e2e spec from disk', () => {
    expect(existsSync(resolve(process.cwd(), 'tests/e2e/rental/contract-workflow.spec.ts'))).toBe(false);
  });

  it('keeps the import success e2e spec free from raw legacy excel import api tokens', () => {
    const source = readSource('tests/e2e/legacy-contract/import-success.spec.ts');

    expect(source).not.toContain('/api/v1/rental-contracts/excel/import');
  });

  it('keeps the import guardrails e2e spec free from raw legacy excel import api tokens', () => {
    const source = readSource('tests/e2e/user/import-guardrails.spec.ts');

    expect(source).not.toContain('/api/v1/rental-contracts/excel/import');
  });

  it('keeps the import success e2e spec free from raw legacy contract filename prefixes', () => {
    const source = readSource('tests/e2e/legacy-contract/import-success.spec.ts');

    expect(source).not.toContain('rent_contract_');
  });

  it('keeps the import success e2e spec free from raw legacy rental route literals', () => {
    const source = readSource('tests/e2e/legacy-contract/import-success.spec.ts');

    expect(source).not.toContain("'/rental/contracts'");
    expect(source).not.toContain("'/rental/contracts/pdf-import'");
  });

  it('keeps the import guardrails e2e spec free from raw legacy rental route literals', () => {
    const source = readSource('tests/e2e/user/import-guardrails.spec.ts');

    expect(source).not.toContain("'/rental/contracts'");
    expect(source).not.toContain("'/rental/contracts/pdf-import'");
  });

  it('keeps the import success e2e spec free from low-value rental describe tags', () => {
    const source = readSource('tests/e2e/legacy-contract/import-success.spec.ts');

    expect(source).not.toContain('@rental-import-success');
  });

  it('keeps the user usability e2e spec free from raw legacy rental route literals', () => {
    const source = readSource('tests/e2e/user/user-usability.spec.ts');

    expect(source).not.toContain("'/rental/contracts'");
    expect(source).not.toContain("'/rental/contracts/create'");
  });

  it('keeps the user usability e2e spec free from stale legacy contract creation assumptions', () => {
    const source = readSource('tests/e2e/user/user-usability.spec.ts');

    expect(source).not.toContain('/创建合同/');
    expect(source).not.toContain('/租金合同管理|合同管理/i');
  });
});
