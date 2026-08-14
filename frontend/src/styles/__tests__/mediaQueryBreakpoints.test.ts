import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const srcRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

function listCssFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return listCssFiles(entryPath);
    }
    return entry.isFile() && entry.name.endsWith('.css') ? [entryPath] : [];
  });
}

describe('媒体查询断点守卫', () => {
  it('原生 @media 条件不得使用 CSS 自定义属性', () => {
    const findings = listCssFiles(srcRoot).flatMap(filePath => {
      const source = readFileSync(filePath, 'utf8');
      return Array.from(source.matchAll(/@media\s*([^{]+){/g))
        .filter(match => match[1].includes('var('))
        .map(match => `${path.relative(srcRoot, filePath)}: ${match[0].trim()}`);
    });

    expect(findings, findings.join('\n')).toEqual([]);
  });
});
