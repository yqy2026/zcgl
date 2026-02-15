#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.resolve(__dirname, '..');
const defaultSrcRoot = path.join(projectRoot, 'src');
const argv = process.argv.slice(2);
const jsonFileFlag = '--json-file';
const srcRootFlag = '--src-root';

const lintDisablePattern = /eslint-disable(?:-next-line|-line)?/;
const textExtensions = new Set(['.ts', '.tsx', '.js', '.jsx', '.d.ts', '.css', '.scss']);

function readArgValue(flag) {
  const index = argv.indexOf(flag);
  if (index < 0) {
    return null;
  }
  return argv[index + 1] ?? null;
}

const jsonFile = readArgValue(jsonFileFlag);
const srcRoot = path.resolve(projectRoot, readArgValue(srcRootFlag) ?? defaultSrcRoot);

function walkFiles(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walkFiles(fullPath));
      continue;
    }
    if (entry.isFile()) {
      files.push(fullPath);
    }
  }

  return files;
}

function isTextFile(filePath) {
  return textExtensions.has(path.extname(filePath));
}

function scanFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/);
  const findings = [];

  lines.forEach((line, index) => {
    if (!lintDisablePattern.test(line)) {
      return;
    }
    findings.push({
      file: path.relative(srcRoot, filePath),
      line: index + 1,
      text: line.trim(),
    });
  });

  return findings;
}

function summarizeByFile(findings) {
  const counts = new Map();
  for (const item of findings) {
    counts.set(item.file, (counts.get(item.file) ?? 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

const files = walkFiles(srcRoot).filter(isTextFile);
const findings = files.flatMap(scanFile);
const fileSummary = summarizeByFile(findings);

console.log('Lint disable comment scan');
console.log(`src: ${srcRoot}`);
console.log(`files scanned: ${files.length}`);
console.log(`eslint-disable findings: ${findings.length}`);
if (fileSummary.length > 0) {
  console.log('top files:');
  fileSummary.slice(0, 20).forEach(([file, count]) => {
    console.log(`  - ${file}: ${count}`);
  });
}

if (jsonFile != null) {
  const payload = {
    srcRoot,
    scannedFiles: files.length,
    totalFindings: findings.length,
    byFile: fileSummary,
    findings,
    passed: findings.length === 0,
  };
  const jsonPath = path.isAbsolute(jsonFile) ? jsonFile : path.resolve(projectRoot, jsonFile);
  fs.mkdirSync(path.dirname(jsonPath), { recursive: true });
  fs.writeFileSync(jsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

if (findings.length > 0) {
  process.exit(1);
}
