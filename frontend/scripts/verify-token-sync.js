#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.resolve(__dirname, '..');
const defaultSharedTokensPath = path.join(projectRoot, 'src', 'theme', 'sharedTokens.ts');
const defaultVariablesCssPath = path.join(projectRoot, 'src', 'styles', 'variables.css');
const argv = process.argv.slice(2);
const jsonFileFlag = '--json-file';
const sharedTokensFileFlag = '--shared-tokens-file';
const variablesCssFileFlag = '--variables-css-file';

function readArgValue(flag) {
  const index = argv.indexOf(flag);
  if (index < 0) {
    return null;
  }
  return argv[index + 1] ?? null;
}

const jsonFile = readArgValue(jsonFileFlag);
const sharedTokensPath = path.resolve(
  projectRoot,
  readArgValue(sharedTokensFileFlag) ?? defaultSharedTokensPath
);
const variablesCssPath = path.resolve(
  projectRoot,
  readArgValue(variablesCssFileFlag) ?? defaultVariablesCssPath
);

function readFile(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function extractBlock(content, blockName) {
  const blockRegex = new RegExp(`${blockName}:\\s*\\{([\\s\\S]*?)\\n\\s*\\}`, 'm');
  const match = content.match(blockRegex);
  return match?.[1] ?? '';
}

function parseTsObjectEntries(blockContent) {
  const entryRegex = /([a-zA-Z0-9_]+)\s*:\s*'([^']+)'/g;
  const result = new Map();
  let match = entryRegex.exec(blockContent);
  while (match != null) {
    result.set(match[1], match[2]);
    match = entryRegex.exec(blockContent);
  }
  return result;
}

function parseCssVariables(content) {
  const varRegex = /--([a-z0-9-]+)\s*:\s*([^;]+);/g;
  const result = new Map();
  let match = varRegex.exec(content);
  while (match != null) {
    result.set(match[1], match[2].trim());
    match = varRegex.exec(content);
  }
  return result;
}

function compareMappings(prefix, tsMap, cssMap, keyMapper) {
  const mismatches = [];
  tsMap.forEach((value, key) => {
    const cssVarName = keyMapper(prefix, key);
    const cssValue = cssMap.get(cssVarName);
    if (cssValue == null) {
      mismatches.push(`missing css var --${cssVarName} (expected ${value})`);
      return;
    }
    if (cssValue !== value) {
      mismatches.push(`--${cssVarName}: expected ${value}, got ${cssValue}`);
    }
  });
  return mismatches;
}

const sharedTokensContent = readFile(sharedTokensPath);
const variablesCssContent = readFile(variablesCssPath);

const spacingMap = parseTsObjectEntries(extractBlock(sharedTokensContent, 'spacing'));
const fontSizeMap = parseTsObjectEntries(extractBlock(sharedTokensContent, 'fontSize'));
const borderRadiusMap = parseTsObjectEntries(extractBlock(sharedTokensContent, 'borderRadius'));
const cssVars = parseCssVariables(variablesCssContent);

const mismatches = [
  ...compareMappings('spacing', spacingMap, cssVars, (prefix, key) => `${prefix}-${key}`),
  ...compareMappings('font-size', fontSizeMap, cssVars, (prefix, key) => `${prefix}-${key}`),
  ...compareMappings('radius', borderRadiusMap, cssVars, (prefix, key) => `${prefix}-${key}`),
];

console.log('Token sync check');
console.log(`shared tokens: ${path.relative(projectRoot, sharedTokensPath)}`);
console.log(`variables css: ${path.relative(projectRoot, variablesCssPath)}`);
console.log(`checked keys: ${spacingMap.size + fontSizeMap.size + borderRadiusMap.size}`);

if (jsonFile != null) {
  const payload = {
    sharedTokensPath: path.relative(projectRoot, sharedTokensPath),
    variablesCssPath: path.relative(projectRoot, variablesCssPath),
    checkedKeys: spacingMap.size + fontSizeMap.size + borderRadiusMap.size,
    mismatches,
    passed: mismatches.length === 0,
  };
  const jsonPath = path.isAbsolute(jsonFile) ? jsonFile : path.resolve(projectRoot, jsonFile);
  fs.mkdirSync(path.dirname(jsonPath), { recursive: true });
  fs.writeFileSync(jsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

if (mismatches.length > 0) {
  console.error('\nToken sync mismatches:');
  mismatches.forEach(item => {
    console.error(`- ${item}`);
  });
  process.exit(1);
}

console.log('status: pass');
