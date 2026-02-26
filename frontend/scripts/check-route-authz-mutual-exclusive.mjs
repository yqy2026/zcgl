#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

const args = process.argv.slice(2);
const fileArgIndex = args.indexOf('--file');
const targetFile =
  fileArgIndex >= 0 && args[fileArgIndex + 1]
    ? path.resolve(process.cwd(), args[fileArgIndex + 1])
    : path.resolve(projectRoot, 'src/routes/AppRoutes.tsx');

async function loadTypeScript() {
  try {
    return await import('typescript');
  } catch {
    // Fall through to local package path.
  }

  const localTsPath = path.resolve(projectRoot, 'node_modules/typescript/lib/typescript.js');
  if (fs.existsSync(localTsPath)) {
    return import(pathToFileURL(localTsPath).href);
  }

  return null;
}

function propertyNameToText(ts, nameNode) {
  if (ts.isIdentifier(nameNode)) {
    return nameNode.text;
  }
  if (ts.isStringLiteralLike(nameNode)) {
    return nameNode.text;
  }
  return null;
}

function isBooleanTrue(ts, expression) {
  if (expression.kind === ts.SyntaxKind.TrueKeyword) {
    return true;
  }
  if (ts.isParenthesizedExpression(expression)) {
    return isBooleanTrue(ts, expression.expression);
  }
  if (ts.isAsExpression(expression) || ts.isTypeAssertionExpression(expression)) {
    return isBooleanTrue(ts, expression.expression);
  }
  return false;
}

function getPropertyAssignment(ts, obj, key) {
  for (const prop of obj.properties) {
    if (!ts.isPropertyAssignment(prop)) {
      continue;
    }
    const name = propertyNameToText(ts, prop.name);
    if (name === key) {
      return prop;
    }
  }
  return null;
}

function resolveRoutePath(ts, obj, fallback) {
  const pathProp = getPropertyAssignment(ts, obj, 'path');
  if (pathProp == null) {
    return fallback;
  }
  const init = pathProp.initializer;
  if (ts.isStringLiteralLike(init)) {
    return init.text;
  }
  return init.getText().trim();
}

function findVariableDeclaration(ts, sourceFile, targetName) {
  let result = null;

  function visit(node) {
    if (result != null) {
      return;
    }

    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.name.text === targetName
    ) {
      result = node;
      return;
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return result;
}

function resolveArrayInitializer(ts, sourceFile, initializer) {
  if (initializer == null) {
    return null;
  }

  if (ts.isArrayLiteralExpression(initializer)) {
    return initializer;
  }

  if (ts.isIdentifier(initializer)) {
    const referencedDeclaration = findVariableDeclaration(ts, sourceFile, initializer.text);
    return resolveArrayInitializer(ts, sourceFile, referencedDeclaration?.initializer ?? null);
  }

  if (ts.isCallExpression(initializer) && initializer.arguments.length > 0) {
    return resolveArrayInitializer(ts, sourceFile, initializer.arguments[0]);
  }

  if (ts.isAsExpression(initializer) || ts.isTypeAssertionExpression(initializer)) {
    return resolveArrayInitializer(ts, sourceFile, initializer.expression);
  }

  if (ts.isParenthesizedExpression(initializer)) {
    return resolveArrayInitializer(ts, sourceFile, initializer.expression);
  }

  return null;
}

function findProtectedRoutesInitializer(ts, sourceFile) {
  const protectedRoutesDeclaration = findVariableDeclaration(ts, sourceFile, 'protectedRoutes');
  if (protectedRoutesDeclaration == null) {
    return null;
  }

  return resolveArrayInitializer(ts, sourceFile, protectedRoutesDeclaration.initializer ?? null);
}

async function main() {
  if (!fs.existsSync(targetFile)) {
    console.error(`[authz-gate] target file not found: ${targetFile}`);
    process.exit(1);
  }

  const ts = await loadTypeScript();
  if (ts == null) {
    console.error('[authz-gate] TypeScript parser is required but not found.');
    console.error('[authz-gate] Run `cd frontend && pnpm install` before executing this gate.');
    process.exit(2);
  }

  const sourceText = fs.readFileSync(targetFile, 'utf8');
  const sourceFile = ts.createSourceFile(
    targetFile,
    sourceText,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX
  );

  const parseDiagnostics = sourceFile.parseDiagnostics ?? [];
  if (parseDiagnostics.length > 0) {
    console.error(`[authz-gate] parse failed: ${targetFile}`);
    for (const diag of parseDiagnostics) {
      const msg = ts.flattenDiagnosticMessageText(diag.messageText, '\n');
      const pos = diag.start ?? 0;
      const loc = sourceFile.getLineAndCharacterOfPosition(pos);
      console.error(`  - ${loc.line + 1}:${loc.character + 1} ${msg}`);
    }
    process.exit(1);
  }

  const protectedRoutes = findProtectedRoutesInitializer(ts, sourceFile);
  if (protectedRoutes == null) {
    console.error('[authz-gate] `protectedRoutes` array literal not found.');
    process.exit(1);
  }

  const violations = [];
  const nonObjectEntries = [];

  for (let index = 0; index < protectedRoutes.elements.length; index += 1) {
    const element = protectedRoutes.elements[index];
    if (!ts.isObjectLiteralExpression(element)) {
      nonObjectEntries.push({
        index: index + 1,
        expression: element.getText(sourceFile).trim(),
      });
      continue;
    }

    const adminOnlyProp = getPropertyAssignment(ts, element, 'adminOnly');
    const permissionsProp = getPropertyAssignment(ts, element, 'permissions');
    const adminOnly = adminOnlyProp != null && isBooleanTrue(ts, adminOnlyProp.initializer);
    const hasPermissions = permissionsProp != null;

    if (adminOnly && hasPermissions) {
      violations.push({
        index: index + 1,
        path: resolveRoutePath(ts, element, `<route#${index + 1}>`),
      });
    }
  }

  if (violations.length > 0) {
    console.error('[authz-gate] D10 violated: found routes with both `adminOnly: true` and `permissions`.');
    for (const item of violations) {
      console.error(`  - #${item.index} path=${item.path}`);
    }
    process.exit(1);
  }

  if (nonObjectEntries.length > 0) {
    console.error('[authz-gate] D10 gate requires object-literal route entries in `protectedRoutes`.');
    for (const item of nonObjectEntries) {
      console.error(`  - #${item.index} entry=${item.expression}`);
    }
    process.exit(1);
  }

  console.log(`[authz-gate] PASS: no D10 violations in ${path.relative(process.cwd(), targetFile)}`);
}

main().catch(error => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(`[authz-gate] unexpected error: ${message}`);
  process.exit(1);
});
