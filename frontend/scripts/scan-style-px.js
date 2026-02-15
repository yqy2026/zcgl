#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.resolve(__dirname, '..');
const defaultSrcRoot = path.join(projectRoot, 'src');
const defaultConfigPath = path.join(__dirname, 'scan-style-px.config.json');
const argv = process.argv.slice(2);
const args = new Set(argv);
const failOnModule = args.has('--fail-on-module');
const failOnNonToken = args.has('--fail-on-non-token');
const failOnToken = args.has('--fail-on-token');
const jsonFileFlag = '--json-file';
const srcRootFlag = '--src-root';
const configFileFlag = '--config-file';

const textExtensions = new Set(['.css', '.scss', '.ts', '.tsx']);
const moduleStylePattern = /\.module\.(css|scss)$/;
const pxPattern = /\b\d+px\b/g;

function readArgValue(flag) {
  const index = argv.indexOf(flag);
  if (index < 0) {
    return null;
  }
  return argv[index + 1] ?? null;
}

const srcRoot = path.resolve(projectRoot, readArgValue(srcRootFlag) ?? defaultSrcRoot);
const configPath = path.resolve(projectRoot, readArgValue(configFileFlag) ?? defaultConfigPath);
const jsonFile = readArgValue(jsonFileFlag);

function loadTokenSourceFiles() {
  if (!fs.existsSync(configPath)) {
    return new Set([
      path.normalize(path.join('styles', 'variables.css')),
      path.normalize(path.join('theme', 'sharedTokens.ts')),
    ]);
  }

  const raw = fs.readFileSync(configPath, 'utf8');
  const parsed = JSON.parse(raw);
  const entries = Array.isArray(parsed?.tokenSourceFiles) ? parsed.tokenSourceFiles : [];
  return new Set(entries.map(item => path.normalize(item)));
}

const tokenSourceFiles = loadTokenSourceFiles();

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

function collectPxHits(filePath) {
  const relativePath = path.relative(srcRoot, filePath);
  const normalizedRelativePath = path.normalize(relativePath);
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/);

  const hits = [];
  lines.forEach((line, index) => {
    const matches = line.match(pxPattern);
    if (matches == null) {
      return;
    }
    hits.push({
      file: normalizedRelativePath,
      line: index + 1,
      values: matches,
    });
  });

  return hits;
}

function summarizeByFile(hits) {
  const fileCounts = new Map();
  for (const hit of hits) {
    const current = fileCounts.get(hit.file) ?? 0;
    fileCounts.set(hit.file, current + hit.values.length);
  }
  return [...fileCounts.entries()].sort((a, b) => b[1] - a[1]);
}

function printSection(title, hits) {
  const total = hits.reduce((acc, item) => acc + item.values.length, 0);
  const fileSummary = summarizeByFile(hits);

  console.log(`\n[${title}]`);
  console.log(`hits: ${total}`);
  console.log(`files: ${fileSummary.length}`);

  if (fileSummary.length > 0) {
    console.log('top files:');
    fileSummary.slice(0, 10).forEach(([file, count]) => {
      console.log(`  - ${file}: ${count}`);
    });
  }
}

function isTextFile(filePath) {
  return textExtensions.has(path.extname(filePath));
}

function isTokenSourceFile(relativePath) {
  return tokenSourceFiles.has(path.normalize(relativePath));
}

const allFiles = walkFiles(srcRoot).filter(isTextFile);

const moduleHits = [];
const nonTokenHits = [];
const tokenSourceHits = [];

for (const filePath of allFiles) {
  const relativePath = path.relative(srcRoot, filePath);
  const hits = collectPxHits(filePath);
  if (hits.length === 0) {
    continue;
  }

  if (moduleStylePattern.test(filePath)) {
    moduleHits.push(...hits);
    continue;
  }

  if (isTokenSourceFile(relativePath)) {
    tokenSourceHits.push(...hits);
    continue;
  }

  nonTokenHits.push(...hits);
}

console.log('Style px scan baseline');
console.log(`src: ${srcRoot}`);
console.log(`config: ${configPath}`);
console.log(
  `token sources: ${[...tokenSourceFiles].map(item => `src/${item}`).join(', ')}`
);

printSection('module-style px', moduleHits);
printSection('non-token-source px', nonTokenHits);
printSection('token-source px', tokenSourceHits);

const shouldFail =
  (failOnModule && moduleHits.length > 0) ||
  (failOnNonToken && nonTokenHits.length > 0) ||
  (failOnToken && tokenSourceHits.length > 0);

if (jsonFile != null) {
  const payload = {
    srcRoot,
    configPath,
    tokenSources: [...tokenSourceFiles].map(item => `src/${item}`),
    sections: {
      module: summarizeByFile(moduleHits),
      nonToken: summarizeByFile(nonTokenHits),
      tokenSource: summarizeByFile(tokenSourceHits),
    },
    totals: {
      module: moduleHits.reduce((acc, item) => acc + item.values.length, 0),
      nonToken: nonTokenHits.reduce((acc, item) => acc + item.values.length, 0),
      tokenSource: tokenSourceHits.reduce((acc, item) => acc + item.values.length, 0),
    },
    strict: {
      failOnModule,
      failOnNonToken,
      failOnToken,
      shouldFail,
    },
  };
  const jsonPath = path.isAbsolute(jsonFile) ? jsonFile : path.resolve(projectRoot, jsonFile);
  fs.mkdirSync(path.dirname(jsonPath), { recursive: true });
  fs.writeFileSync(jsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

if (shouldFail) {
  console.error('\nscan failed: strict conditions were not met');
  process.exit(1);
}
