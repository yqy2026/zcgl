#!/usr/bin/env node

/**
 * Token 单一真相源校验（verify-token-sync）
 *
 * 设计系统收口后（2026-08-13），token 只有两层：
 *   - CSS 层：src/styles/variables.css（真相源）
 *   - AntD 层：src/themeConfig.ts（必须与 CSS 层同值）
 * 本脚本断言两层重叠 token 的值完全一致，防止第三套取值漂移。
 * rem → px 按 16px 根字号换算（html 根字号已固定 16px）。
 */

const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.resolve(__dirname, '..');
const defaultThemeConfigPath = path.join(projectRoot, 'src', 'themeConfig.ts');
const defaultVariablesCssPath = path.join(projectRoot, 'src', 'styles', 'variables.css');
const argv = process.argv.slice(2);
const jsonFileFlag = '--json-file';
const themeConfigFileFlag = '--theme-config-file';
const variablesCssFileFlag = '--variables-css-file';

function readArgValue(flag) {
  const index = argv.indexOf(flag);
  return index < 0 ? null : (argv[index + 1] ?? null);
}

const jsonFile = readArgValue(jsonFileFlag);
const themeConfigPath = path.resolve(
  projectRoot,
  readArgValue(themeConfigFileFlag) ?? defaultThemeConfigPath
);
const variablesCssPath = path.resolve(
  projectRoot,
  readArgValue(variablesCssFileFlag) ?? defaultVariablesCssPath
);

function readFile(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function parseCssVariables(content) {
  // 只解析顶层 :root 块（不含 prefers-contrast 等媒体查询 remap）
  const rootBlock = content.match(/:root\s*\{([\s\S]*?)\n\}/);
  const blockContent = rootBlock?.[1] ?? '';
  const varRegex = /--([a-z0-9-]+)\s*:\s*([^;]+);/g;
  const result = new Map();
  let match = varRegex.exec(blockContent);
  while (match != null) {
    result.set(match[1], match[2].trim());
    match = varRegex.exec(blockContent);
  }
  return result;
}

// themeConfig.ts 顶层 token 块：colorPrimary: '#0e63e5', fontSize: 14, borderRadius: 8
function parseThemeConfigTokens(content) {
  const tokenBlock = content.match(/token:\s*\{([\s\S]*?)\n\s*\},/);
  const blockContent = tokenBlock?.[1] ?? '';
  const entryRegex = /([a-zA-Z0-9_]+)\s*:\s*('([^']+)'|([0-9.]+))/g;
  const result = new Map();
  let match = entryRegex.exec(blockContent);
  while (match != null) {
    result.set(match[1], match[3] ?? match[4]);
    match = entryRegex.exec(blockContent);
  }
  return result;
}

// rem → px（16px 根字号）；其余原样
function normalize(value) {
  const rem = value.match(/^([0-9.]+)rem$/);
  if (rem != null) {
    return String(Math.round(Number(rem[1]) * 16 * 100) / 100);
  }
  return value;
}

// themeConfig 键 → CSS 变量名映射（仅重叠 token，值需经 normalize 对齐）
const TOKEN_MAP = [
  ['colorPrimary', 'color-primary'],
  ['colorPrimaryHover', 'color-primary-hover'],
  ['colorPrimaryActive', 'color-primary-active'],
  ['colorInfo', 'color-info'],
  ['colorSuccess', 'color-success'],
  ['colorWarning', 'color-warning'],
  ['colorError', 'color-error'],
  ['colorBgLayout', 'color-bg-layout'],
  ['colorBgContainer', 'color-bg-primary'],
  ['colorText', 'color-text-primary'],
  ['colorTextSecondary', 'color-text-secondary'],
  ['colorTextTertiary', 'color-text-tertiary'],
  ['colorTextQuaternary', 'color-text-quaternary'],
  ['colorTextHeading', 'color-text-primary'],
  ['fontSize', 'font-size-base'],
  ['borderRadius', 'radius-md'],
];

const themeConfigTokens = parseThemeConfigTokens(readFile(themeConfigPath));
const cssVars = parseCssVariables(readFile(variablesCssPath));

const mismatches = [];
for (const [themeKey, cssVarName] of TOKEN_MAP) {
  const expected = themeConfigTokens.get(themeKey);
  if (expected == null) {
    mismatches.push(`missing themeConfig token ${themeKey}`);
    continue;
  }
  const cssValue = cssVars.get(cssVarName);
  if (cssValue == null) {
    mismatches.push(`missing css var --${cssVarName} (expected ${expected})`);
    continue;
  }
  if (normalize(cssValue) !== expected) {
    mismatches.push(`--${cssVarName}: themeConfig ${expected}, variables.css ${cssValue}`);
  }
}

console.log('Token sync check');
console.log(`theme config: ${path.relative(projectRoot, themeConfigPath)}`);
console.log(`variables css: ${path.relative(projectRoot, variablesCssPath)}`);
console.log(`checked keys: ${TOKEN_MAP.length}`);

if (jsonFile != null) {
  const payload = {
    themeConfigPath: path.relative(projectRoot, themeConfigPath),
    variablesCssPath: path.relative(projectRoot, variablesCssPath),
    checkedKeys: TOKEN_MAP.length,
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
