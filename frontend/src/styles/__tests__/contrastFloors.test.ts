/**
 * 对比度地板测试（WCAG AA 4.5:1）
 *
 * 本测试把审计结论固化为回归防线（issue：主按钮 4.10、三级文本 3.36、
 * 语义 Tag 1.8–3.0、图表色板重复/近似）。token 值变化若跌破地板，本测试失败。
 * 值来源：variables.css 是 CSS 变量层唯一真相源，测试直接解析该文件。
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { CHART_COLORS, CHART_LABEL_COLORS } from '@/styles/colorMap';
import { baseThemeConfig } from '@/themeConfig';

const cssFile = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../variables.css');
const globalCssFile = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../global.css');
const cssSource = readFileSync(cssFile, 'utf8');
const globalCssSource = readFileSync(globalCssFile, 'utf8');

function resolveToken(name: string): string {
  const match = cssSource.match(new RegExp(`--${name}:\\s*([^;]+);`));
  if (match == null) throw new Error(`token --${name} not found in variables.css`);
  return match[1].trim();
}

function parseColor(value: string): [number, number, number] {
  const hex = value.match(/^#([0-9a-f]{6})$/i);
  if (hex != null) {
    const c = hex[1];
    return [0, 2, 4].map(i => parseInt(c.slice(i, i + 2), 16)) as [number, number, number];
  }
  const rgb = value.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/);
  if (rgb != null) return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])];
  throw new Error(`unsupported color format: ${value}`);
}

function luminance(value: string): number {
  const [r, g, b] = parseColor(value).map(v => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

function hue(hex: string): number {
  const [r, g, b] = parseColor(hex).map(v => v / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  if (d === 0) return 0;
  let h: number;
  if (max === r) h = ((g - b) / d) % 6;
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  return (h * 60 + 360) % 360;
}

function hueDistance(a: number, b: number): number {
  const d = Math.abs(a - b);
  return Math.min(d, 360 - d);
}

const AA = 4.5;

describe('对比度地板（WCAG AA）', () => {
  it('主按钮白字 on 主色 ≥ 4.5:1', () => {
    expect(contrast('#ffffff', resolveToken('color-primary'))).toBeGreaterThanOrEqual(AA);
  });

  it('主色悬停档白字 ≥ 4.5:1（按钮/链接 hover 态）', () => {
    expect(contrast('#ffffff', resolveToken('color-primary-hover'))).toBeGreaterThanOrEqual(AA);
  });

  it('三级文本 on 白底与布局灰蓝 ≥ 4.5:1', () => {
    const tertiary = resolveToken('color-text-tertiary');
    expect(contrast(tertiary, '#ffffff')).toBeGreaterThanOrEqual(AA);
    expect(contrast(tertiary, resolveToken('color-bg-layout'))).toBeGreaterThanOrEqual(AA);
  });

  it('Tag 状态文字色 on 对应浅底 ≥ 4.5:1', () => {
    const pairs: Array<[string, string, string]> = [
      ['blue', 'color-blue-text', '#e6f4ff'],
      ['green', 'color-green-text', '#f6ffed'],
      ['gold', 'color-gold-text', '#fffbe6'],
      ['red', 'color-red-text', '#fff2f0'],
      ['cyan', 'color-cyan-text', '#e6fffb'],
      ['orange', 'color-orange-text', '#fff7e6'],
      ['lime', 'color-lime-text', '#fcffe6'],
      ['volcano', 'color-volcano-text', '#fff2e8'],
      // antd 状态预设：success/warning/error/processing 映射到对应深色文字 token
      ['success', 'color-green-text', '#f6ffed'],
      ['warning', 'color-gold-text', '#fffbe6'],
      ['error', 'color-red-text', '#fff2f0'],
      ['processing', 'color-blue-text', '#e6f4ff'],
    ];
    for (const [preset, token, bg] of pairs) {
      const value = resolveToken(token);
      expect(contrast(value, bg), `--${token} (${value}) on ${bg}`).toBeGreaterThanOrEqual(AA);
      expect(globalCssSource).toContain(`.ant-tag.ant-tag-${preset}:not(.ant-tag-disabled)`);
      expect(globalCssSource).toContain(`color: var(--${token});`);
    }
  });
});

describe('themeConfig ↔ variables.css 同值（单一真相源）', () => {
  // themeConfig 键 → CSS 变量名；AntD 层不得出现与 CSS 层不同的取值
  const SYNC_MAP: Array<[keyof NonNullable<typeof baseThemeConfig.token>, string]> = [
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
  ];

  it('重叠 token 值逐项一致', () => {
    const tokens = baseThemeConfig.token ?? {};
    for (const [themeKey, cssVarName] of SYNC_MAP) {
      const expected = tokens[themeKey];
      expect(String(expected), `themeConfig.${themeKey} 应等于 --${cssVarName}`).toBe(
        resolveToken(cssVarName)
      );
    }
  });
});

describe('图表色板感知距离', () => {
  it('CHART_LABEL_COLORS 字面值与对应 token 严格一致（G2 label fill 不支持 var()）', () => {
    expect(CHART_LABEL_COLORS.light).toBe(resolveToken('color-bg-primary'));
    expect(CHART_LABEL_COLORS.medium).toBe(resolveToken('color-text-secondary'));
    expect(CHART_LABEL_COLORS.dark).toBe(resolveToken('color-text-primary'));
  });

  it('CHART_COLORS 为 8 个去重颜色，相邻色相距离 ≥ 30°', () => {
    const values = CHART_COLORS.map(v => {
      const tokenMatch = v.match(/^var\(--([a-z0-9-]+)\)$/);
      if (tokenMatch == null) throw new Error(`CHART_COLORS entry is not a bare var(): ${v}`);
      return resolveToken(tokenMatch[1]);
    });

    expect(new Set(values).size).toBe(values.length);

    const hues = values.map(hue);
    for (let i = 0; i < hues.length; i += 1) {
      const distance = hueDistance(hues[i], hues[(i + 1) % hues.length]);
      expect(distance, `相邻色相距离 ${i}→${(i + 1) % hues.length} 为 ${distance.toFixed(1)}°`).toBeGreaterThanOrEqual(30);
    }
  });
});
