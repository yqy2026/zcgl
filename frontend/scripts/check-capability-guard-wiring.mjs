#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

const appFile = path.resolve(projectRoot, 'src/App.tsx');
const appRoutesFile = path.resolve(projectRoot, 'src/routes/AppRoutes.tsx');

function assertFileExists(filePath, label) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`[capability-guard-wiring] missing ${label}: ${path.relative(projectRoot, filePath)}`);
  }
}

function assertPattern(content, regex, message) {
  if (!regex.test(content)) {
    throw new Error(message);
  }
}

function main() {
  assertFileExists(appFile, 'App route chain file');
  assertFileExists(appRoutesFile, 'App route metadata file');

  const appContent = fs.readFileSync(appFile, 'utf8');
  const appRoutesContent = fs.readFileSync(appRoutesFile, 'utf8');

  assertPattern(
    appContent,
    /VITE_ENABLE_CAPABILITY_GUARD/,
    '[capability-guard-wiring] App.tsx must reference VITE_ENABLE_CAPABILITY_GUARD.'
  );

  assertPattern(
    appContent,
    /capabilityGuardEnabled/,
    '[capability-guard-wiring] App.tsx must define capabilityGuardEnabled.'
  );

  assertPattern(
    appContent,
    /renderProtectedElement/,
    '[capability-guard-wiring] App.tsx must use renderProtectedElement route guard chain.'
  );

  assertPattern(
    appContent,
    /adminOnly|permissions|permissionMode/,
    '[capability-guard-wiring] App.tsx must include adminOnly/permissions guard branch evidence.'
  );

  assertPattern(
    appContent,
    /<PermissionGuard[\s\S]*permissions=/,
    '[capability-guard-wiring] App.tsx must wrap guarded routes with PermissionGuard when capability guard is enabled.'
  );

  assertPattern(
    appRoutesContent,
    /adminOnly|permissions|permissionMode/,
    '[capability-guard-wiring] AppRoutes.tsx must contain route auth metadata fields.'
  );

  console.log('[capability-guard-wiring] PASS: capability guard wiring evidence found in App.tsx and AppRoutes.tsx.');
}

try {
  main();
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(message);
  process.exit(1);
}
