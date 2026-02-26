#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

const defaultTargets = [
  'src/constants/routes.ts',
  'src/routes/AppRoutes.tsx',
  'src/contexts/AuthContext.tsx',
  'src/components/System/CapabilityGuard.tsx',
  'src/hooks/usePermission.tsx',
];

const forbiddenActions = new Set([
  'view',
  'edit',
  'import',
  'settings',
  'logs',
  'dictionary',
  'lock',
  'assign_permissions',
]);

const forbiddenResources = new Set([
  'rental',
  'system',
  'users',
  'roles',
  'organizations',
  'assets',
]);

async function loadTypeScript() {
  try {
    return await import('typescript');
  } catch {
    // noop
  }

  const localTsPath = path.resolve(projectRoot, 'node_modules/typescript/lib/typescript.js');
  if (fs.existsSync(localTsPath)) {
    return import(pathToFileURL(localTsPath).href);
  }

  return null;
}

function propertyNameToText(ts, nameNode) {
  if (ts.isIdentifier(nameNode)) return nameNode.text;
  if (ts.isStringLiteralLike(nameNode)) return nameNode.text;
  return null;
}

function getStringLiteral(ts, node) {
  if (ts.isStringLiteralLike(node)) {
    return node.text;
  }
  if (ts.isNoSubstitutionTemplateLiteral(node)) {
    return node.text;
  }
  if (ts.isParenthesizedExpression(node)) {
    return getStringLiteral(ts, node.expression);
  }
  if (ts.isAsExpression(node) || ts.isTypeAssertionExpression(node)) {
    return getStringLiteral(ts, node.expression);
  }
  return null;
}

function collectViolations(ts, sourceFile) {
  const violations = [];

  function visit(node) {
    if (ts.isObjectLiteralExpression(node)) {
      for (const prop of node.properties) {
        if (!ts.isPropertyAssignment(prop)) continue;
        const key = propertyNameToText(ts, prop.name);
        if (key == null) continue;

        const literal = getStringLiteral(ts, prop.initializer);
        if (literal == null) continue;

        if (key === 'action' && forbiddenActions.has(literal)) {
          const pos = sourceFile.getLineAndCharacterOfPosition(prop.getStart(sourceFile));
          violations.push({
            kind: 'action',
            value: literal,
            line: pos.line + 1,
            col: pos.character + 1,
          });
        }

        if (key === 'resource' && forbiddenResources.has(literal)) {
          const pos = sourceFile.getLineAndCharacterOfPosition(prop.getStart(sourceFile));
          violations.push({
            kind: 'resource',
            value: literal,
            line: pos.line + 1,
            col: pos.character + 1,
          });
        }
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return violations;
}

async function main() {
  const ts = await loadTypeScript();
  if (ts == null) {
    console.error('[authz-vocabulary-gate] TypeScript parser not found. Run `cd frontend && pnpm install`.');
    process.exit(2);
  }

  const targets = defaultTargets
    .map(rel => path.resolve(projectRoot, rel))
    .filter(abs => fs.existsSync(abs));

  if (targets.length === 0) {
    console.error('[authz-vocabulary-gate] no target files found.');
    process.exit(1);
  }

  const allViolations = [];

  for (const filePath of targets) {
    const content = fs.readFileSync(filePath, 'utf8');
    const sourceFile = ts.createSourceFile(
      filePath,
      content,
      ts.ScriptTarget.Latest,
      true,
      filePath.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
    );

    const parseDiagnostics = sourceFile.parseDiagnostics ?? [];
    if (parseDiagnostics.length > 0) {
      console.error(`[authz-vocabulary-gate] parse failed: ${path.relative(projectRoot, filePath)}`);
      for (const diag of parseDiagnostics) {
        const msg = ts.flattenDiagnosticMessageText(diag.messageText, '\n');
        const pos = diag.start ?? 0;
        const loc = sourceFile.getLineAndCharacterOfPosition(pos);
        console.error(`  - ${loc.line + 1}:${loc.character + 1} ${msg}`);
      }
      process.exit(1);
    }

    const violations = collectViolations(ts, sourceFile);
    for (const violation of violations) {
      allViolations.push({
        file: path.relative(projectRoot, filePath),
        ...violation,
      });
    }
  }

  if (allViolations.length > 0) {
    console.error('[authz-vocabulary-gate] FAILED: forbidden authz vocabulary found.');
    for (const item of allViolations) {
      console.error(
        `  - ${item.file}:${item.line}:${item.col} ${item.kind}='${item.value}' is not allowed in Phase 3 guard chain`
      );
    }
    process.exit(1);
  }

  console.log(`[authz-vocabulary-gate] PASS: checked ${targets.length} file(s), no forbidden action/resource literals.`);
}

main().catch(error => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(`[authz-vocabulary-gate] unexpected error: ${message}`);
  process.exit(1);
});
