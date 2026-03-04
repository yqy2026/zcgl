import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

const isWindows = process.platform === 'win32';
const binDir = join(process.cwd(), 'node_modules', '.bin');
const tsgoBinary = join(binDir, isWindows ? 'tsgo.cmd' : 'tsgo');
const tscBinary = join(binDir, isWindows ? 'tsc.cmd' : 'tsc');

const args = process.argv.slice(2);

let compiler = 'tsgo';
if (!existsSync(tsgoBinary)) {
  compiler = 'tsc';
  console.warn(
    '[type-check] tsgo is unavailable in this environment, fallback to tsc.',
  );
}

if (compiler === 'tsc' && !existsSync(tscBinary)) {
  console.error(
    `[type-check] Missing compiler binary: ${tscBinary}. Run "pnpm install" first.`,
  );
  process.exit(1);
}

const result = spawnSync(
  'pnpm',
  ['exec', '--', compiler, ...args],
  {
    stdio: 'inherit',
    shell: isWindows,
  },
);

if (result.error) {
  console.error(
    `[type-check] Failed to execute ${compiler}: ${result.error.message}`,
  );
  process.exit(1);
}

process.exit(result.status ?? 1);
