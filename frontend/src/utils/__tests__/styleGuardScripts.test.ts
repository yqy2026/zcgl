import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { execFile } from 'node:child_process';
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

interface ScriptResult {
  code: number;
  stdout: string;
  stderr: string;
}

interface ScanReport {
  totals: {
    module: number;
    nonToken: number;
    tokenSource: number;
  };
  strict: {
    shouldFail: boolean;
  };
}

interface TokenSyncReport {
  themeConfigPath: string;
  variablesCssPath: string;
  checkedKeys: number;
  mismatches: string[];
  passed: boolean;
}

interface LintDisableReport {
  scannedFiles: number;
  totalFindings: number;
  passed: boolean;
  findings: Array<{
    file: string;
    line: number;
    text: string;
  }>;
}

const currentFilePath = fileURLToPath(import.meta.url);
const currentDirPath = path.dirname(currentFilePath);
const frontendRoot = path.resolve(currentDirPath, '../../../');
const scanScriptPath = path.join(frontendRoot, 'scripts', 'scan-style-px.js');
const verifyScriptPath = path.join(frontendRoot, 'scripts', 'verify-token-sync.js');
const lintDisableScriptPath = path.join(frontendRoot, 'scripts', 'scan-lint-disable-comments.js');

let tempRoot = '';

function writeFixtureFile(relativePath: string, content: string): string {
  const filePath = path.join(tempRoot, relativePath);
  mkdirSync(path.dirname(filePath), { recursive: true });
  writeFileSync(filePath, content, 'utf8');
  return filePath;
}

function readJsonFile<T>(filePath: string): T {
  return JSON.parse(readFileSync(filePath, 'utf8')) as T;
}

function runNodeScript(scriptPath: string, args: string[]): Promise<ScriptResult> {
  return new Promise(resolve => {
    execFile('node', [scriptPath, ...args], { cwd: frontendRoot }, (error, stdout, stderr) => {
      const errorCode =
        error != null && typeof (error as { code?: unknown }).code === 'number'
          ? ((error as { code: number }).code ?? 1)
          : 0;
      resolve({
        code: errorCode,
        stdout,
        stderr,
      });
    });
  });
}

describe('Style Guard Scripts', () => {
  beforeEach(() => {
    tempRoot = mkdtempSync(path.join(tmpdir(), 'style-guard-scripts-'));
  });

  afterEach(() => {
    if (tempRoot !== '') {
      rmSync(tempRoot, { recursive: true, force: true });
      tempRoot = '';
    }
  });

  it('scan-style-px should pass on clean fixture and export report', async () => {
    const srcRoot = path.join(tempRoot, 'src');
    const configPath = writeFixtureFile(
      'scan-style-px.config.json',
      JSON.stringify(
        {
          tokenSourceFiles: ['styles/variables.css', 'theme/sharedTokens.ts'],
        },
        null,
        2
      )
    );
    const reportPath = path.join(tempRoot, 'scan-report.json');

    writeFixtureFile(
      'src/styles/variables.css',
      `:root {
  --spacing-md: 1rem;
}
`
    );
    writeFixtureFile(
      'src/theme/sharedTokens.ts',
      `export const SHARED_THEME_TOKENS = {
  spacing: {
    md: '1rem',
  },
};
`
    );
    writeFixtureFile(
      'src/components/Button.module.css',
      `.button {
  margin: var(--spacing-md);
}
`
    );

    const result = await runNodeScript(scanScriptPath, [
      '--src-root',
      srcRoot,
      '--config-file',
      configPath,
      '--json-file',
      reportPath,
      '--fail-on-module',
      '--fail-on-non-token',
      '--fail-on-token',
    ]);

    expect(result.code).toBe(0);
    expect(existsSync(reportPath)).toBe(true);
    const report = readJsonFile<ScanReport>(reportPath);
    expect(report.totals.module).toBe(0);
    expect(report.totals.nonToken).toBe(0);
    expect(report.totals.tokenSource).toBe(0);
    expect(report.strict.shouldFail).toBe(false);
  });

  it('scan-style-px should fail when token source contains px and strict token check is enabled', async () => {
    const srcRoot = path.join(tempRoot, 'src');
    const configPath = writeFixtureFile(
      'scan-style-px.config.json',
      JSON.stringify(
        {
          tokenSourceFiles: ['styles/variables.css'],
        },
        null,
        2
      )
    );
    const reportPath = path.join(tempRoot, 'scan-report-strict-token.json');

    const pxUnit = 'px';
    writeFixtureFile(
      'src/styles/variables.css',
      `:root {
  --spacing-md: 16${pxUnit};
}
`
    );

    const result = await runNodeScript(scanScriptPath, [
      '--src-root',
      srcRoot,
      '--config-file',
      configPath,
      '--json-file',
      reportPath,
      '--fail-on-token',
    ]);

    expect(result.code).toBe(1);
    expect(result.stderr).toContain('scan failed');
    const report = readJsonFile<ScanReport>(reportPath);
    expect(report.totals.tokenSource).toBeGreaterThan(0);
    expect(report.strict.shouldFail).toBe(true);
  });

  it('verify-token-sync should pass for aligned token fixtures', async () => {
    const themeConfigPath = writeFixtureFile(
      'fixtures/themeConfig.ts',
      `export const baseThemeConfig = {
  token: {
    colorPrimary: '#0e63e5',
    colorPrimaryHover: '#1169f0',
    colorPrimaryActive: '#0958d9',
    colorInfo: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorBgLayout: '#f0f2f5',
    colorBgContainer: '#ffffff',
    colorText: '#262626',
    colorTextSecondary: '#595959',
    colorTextTertiary: '#717171',
    colorTextQuaternary: '#bfbfbf',
    colorTextHeading: '#262626',
    fontSize: 14,
    borderRadius: 8,
  },
};
`
    );
    const variablesCssPath = writeFixtureFile(
      'fixtures/variables.css',
      `:root {
  --color-primary: #0e63e5;
  --color-primary-hover: #1169f0;
  --color-primary-active: #0958d9;
  --color-info: #1677ff;
  --color-success: #52c41a;
  --color-warning: #faad14;
  --color-error: #ff4d4f;
  --color-bg-layout: #f0f2f5;
  --color-bg-primary: #ffffff;
  --color-text-primary: #262626;
  --color-text-secondary: #595959;
  --color-text-tertiary: #717171;
  --color-text-quaternary: #bfbfbf;
  --font-size-base: 0.875rem;
  --radius-md: 0.5rem;
}
`
    );
    const reportPath = path.join(tempRoot, 'token-sync-pass-report.json');

    const result = await runNodeScript(verifyScriptPath, [
      '--theme-config-file',
      themeConfigPath,
      '--variables-css-file',
      variablesCssPath,
      '--json-file',
      reportPath,
    ]);

    expect(result.code).toBe(0);
    const report = readJsonFile<TokenSyncReport>(reportPath);
    expect(report.themeConfigPath).toBe(path.relative(frontendRoot, themeConfigPath));
    expect(report.variablesCssPath).toBe(path.relative(frontendRoot, variablesCssPath));
    expect(report.checkedKeys).toBe(16);
    expect(report.passed).toBe(true);
    expect(report.mismatches).toHaveLength(0);
  });

  it('verify-token-sync should fail when token value mismatches', async () => {
    const themeConfigPath = writeFixtureFile(
      'fixtures/themeConfig.ts',
      `export const baseThemeConfig = {
  token: {
    colorPrimary: '#0e63e5',
    colorPrimaryHover: '#1169f0',
    colorPrimaryActive: '#0958d9',
    colorInfo: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorBgLayout: '#f0f2f5',
    colorBgContainer: '#ffffff',
    colorText: '#262626',
    colorTextSecondary: '#595959',
    colorTextTertiary: '#717171',
    colorTextQuaternary: '#bfbfbf',
    colorTextHeading: '#262626',
    fontSize: 14,
    borderRadius: 8,
  },
};
`
    );
    const variablesCssPath = writeFixtureFile(
      'fixtures/variables.css',
      `:root {
  --color-primary: #1677ff;
  --color-primary-hover: #1169f0;
  --color-primary-active: #0958d9;
  --color-info: #1677ff;
  --color-success: #52c41a;
  --color-warning: #faad14;
  --color-error: #ff4d4f;
  --color-bg-layout: #f0f2f5;
  --color-bg-primary: #ffffff;
  --color-text-primary: #262626;
  --color-text-secondary: #595959;
  --color-text-tertiary: #717171;
  --color-text-quaternary: #bfbfbf;
  --font-size-base: 0.875rem;
  --radius-md: 0.5rem;
}
`
    );
    const reportPath = path.join(tempRoot, 'token-sync-fail-report.json');

    const result = await runNodeScript(verifyScriptPath, [
      '--theme-config-file',
      themeConfigPath,
      '--variables-css-file',
      variablesCssPath,
      '--json-file',
      reportPath,
    ]);

    expect(result.code).toBe(1);
    expect(result.stderr).toContain('Token sync mismatches');
    const report = readJsonFile<TokenSyncReport>(reportPath);
    expect(report.themeConfigPath).toBe(path.relative(frontendRoot, themeConfigPath));
    expect(report.passed).toBe(false);
    expect(report.mismatches).toContain(
      '--color-primary: themeConfig #0e63e5, variables.css #1677ff'
    );
  });

  it('scan-lint-disable-comments should pass when no directive marker exists', async () => {
    const srcRoot = path.join(tempRoot, 'src');
    const reportPath = path.join(tempRoot, 'lint-disable-pass-report.json');

    writeFixtureFile(
      'src/components/feature.ts',
      `export function feature() {
  return 'ok';
}
`
    );

    const result = await runNodeScript(lintDisableScriptPath, [
      '--src-root',
      srcRoot,
      '--json-file',
      reportPath,
    ]);

    expect(result.code).toBe(0);
    const report = readJsonFile<LintDisableReport>(reportPath);
    expect(report.scannedFiles).toBe(1);
    expect(report.totalFindings).toBe(0);
    expect(report.passed).toBe(true);
  });

  it('scan-lint-disable-comments should fail when directive marker exists', async () => {
    const srcRoot = path.join(tempRoot, 'src');
    const reportPath = path.join(tempRoot, 'lint-disable-fail-report.json');
    const directiveMarker = ['eslint', 'disable-next-line'].join('-');

    writeFixtureFile(
      'src/components/feature.ts',
      `// ${directiveMarker} no-console
console.log('x');
`
    );

    const result = await runNodeScript(lintDisableScriptPath, [
      '--src-root',
      srcRoot,
      '--json-file',
      reportPath,
    ]);

    expect(result.code).toBe(1);
    const report = readJsonFile<LintDisableReport>(reportPath);
    expect(report.totalFindings).toBe(1);
    expect(report.passed).toBe(false);
    expect(report.findings[0]?.file).toContain('feature.ts');
  });
});
