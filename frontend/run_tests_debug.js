const { spawn } = require('child_process');
const path = require('path');

console.log('Starting test run...');

const isWin = process.platform === 'win32';
const npmCmd = isWin ? 'npm.cmd' : 'npm';
const npxCmd = isWin ? 'npx.cmd' : 'npx';

// Try running tsc first
console.log('\n--- Running TSC ---');
const tsc = spawn(npxCmd, ['tsc', '--noEmit'], {
  cwd: path.resolve('frontend'),
  shell: true
});

tsc.stdout.on('data', (data) => console.log(`TSC STDOUT: ${data}`));
tsc.stderr.on('data', (data) => console.log(`TSC STDERR: ${data}`));
tsc.on('close', (code) => {
  console.log(`TSC exited with code ${code}`);

  // Then run vitest
  console.log('\n--- Running Vitest ---');
  const vitest = spawn(npxCmd, ['vitest', 'run', 'src/utils/__tests__/responseExtractor.test.ts', '--no-color'], {
    cwd: path.resolve('frontend'),
    shell: true,
    env: { ...process.env, CI: 'true' }
  });

  vitest.stdout.on('data', (data) => console.log(`VITEST STDOUT: ${data}`));
  vitest.stderr.on('data', (data) => console.log(`VITEST STDERR: ${data}`));
  vitest.on('close', (code) => console.log(`Vitest exited with code ${code}`));
});
