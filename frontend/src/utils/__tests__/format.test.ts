/**
 * 格式化工具测试
 */

import { describe, it, expect } from 'vitest';

import {
  formatNumber,
  formatArea,
  formatPercentage,
  formatDate,
  formatFileSize,
  formatCurrency,
  truncateText,
  getStatusColor,
  calculateOccupancyRate,
  isValidNumber,
  safeNumber,
} from '../format';

describe('formatNumber', () => {
  it('应该格式化数字为千分位', () => {
    expect(formatNumber(1000000)).toBe('1,000,000');
  });

  it('应该格式化小数', () => {
    expect(formatNumber(1234.56)).toBe('1,234.56');
  });

  it('应该格式化字符串数字', () => {
    expect(formatNumber('1000')).toBe('1,000');
  });

  it('应该返回 - 当值为 undefined', () => {
    expect(formatNumber(undefined)).toBe('-');
  });

  it('应该返回 - 当值为 null', () => {
    expect(formatNumber(null)).toBe('-');
  });

  it('应该返回 - 当值为空字符串', () => {
    expect(formatNumber('')).toBe('-');
  });

  it('应该返回 - 当值为非数字字符串', () => {
    expect(formatNumber('abc')).toBe('-');
  });

  it('应该正确格式化零', () => {
    expect(formatNumber(0)).toBe('0');
  });
});

describe('formatArea', () => {
  it('应该格式化面积并添加单位', () => {
    expect(formatArea(1000)).toBe('1,000 ㎡');
  });

  it('应该格式化小数面积', () => {
    expect(formatArea(1234.56)).toBe('1,234.56 ㎡');
  });

  it('应该格式化字符串面积', () => {
    expect(formatArea('500')).toBe('500 ㎡');
  });

  it('应该返回 - 当值为 undefined', () => {
    expect(formatArea(undefined)).toBe('-');
  });

  it('应该返回 - 当值为 null', () => {
    expect(formatArea(null)).toBe('-');
  });

  it('应该返回 - 当值为非数字字符串', () => {
    expect(formatArea('abc')).toBe('-');
  });
});

describe('formatPercentage', () => {
  it('应该格式化百分比', () => {
    expect(formatPercentage(85)).toBe('85.00%');
  });

  it('应该格式化小数百分比', () => {
    expect(formatPercentage(85.567)).toBe('85.57%');
  });

  it('应该格式化字符串百分比', () => {
    expect(formatPercentage('50')).toBe('50.00%');
  });

  it('应该返回 - 当值为 undefined', () => {
    expect(formatPercentage(undefined)).toBe('-');
  });

  it('应该返回 - 当值为 null', () => {
    expect(formatPercentage(null)).toBe('-');
  });

  it('应该格式化零百分比', () => {
    expect(formatPercentage(0)).toBe('0.00%');
  });
});

describe('formatDate', () => {
  it('应该格式化日期字符串', () => {
    const result = formatDate('2024-01-15');
    expect(result).toMatch(/2024/);
  });

  it('应该格式化 Date 对象', () => {
    const result = formatDate(new Date('2024-01-15'));
    expect(result).toMatch(/2024/);
  });

  it('应该返回 - 当值为 null', () => {
    expect(formatDate(null)).toBe('-');
  });

  it('应该返回 - 当值为 undefined', () => {
    expect(formatDate(undefined)).toBe('-');
  });

  it('应该返回 - 当日期无效', () => {
    expect(formatDate('invalid-date')).toBe('-');
  });

  it('应该支持 datetime 格式', () => {
    const result = formatDate('2024-01-15T10:30:00', 'datetime');
    expect(result).toMatch(/2024/);
  });

  it('应该支持 time 格式', () => {
    const result = formatDate('2024-01-15T10:30:00', 'time');
    expect(result).toBeDefined();
  });
});

describe('formatFileSize', () => {
  it('应该格式化字节', () => {
    expect(formatFileSize(500)).toBe('500 B');
  });

  it('应该格式化 KB', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
  });

  it('应该格式化 MB', () => {
    expect(formatFileSize(1024 * 1024)).toBe('1 MB');
  });

  it('应该格式化 GB', () => {
    expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB');
  });

  it('应该返回 0 B 当值为 0', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('应该格式化带小数的大小', () => {
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });
});

describe('formatCurrency', () => {
  it('应该格式化货币（默认人民币）', () => {
    expect(formatCurrency(1000)).toBe('¥1,000');
  });

  it('应该格式化货币（自定义符号）', () => {
    expect(formatCurrency(1000, '$')).toBe('$1,000');
  });

  it('应该返回 - 当值为 undefined', () => {
    expect(formatCurrency(undefined)).toBe('-');
  });

  it('应该返回 - 当值为 null', () => {
    expect(formatCurrency(null)).toBe('-');
  });

  it('应该格式化零', () => {
    expect(formatCurrency(0)).toBe('¥0');
  });
});

describe('truncateText', () => {
  it('应该截断超长文本', () => {
    expect(truncateText('这是一段很长的文本内容', 5)).toBe('这是一段很...');
  });

  it('不应该截断短文本', () => {
    expect(truncateText('短文本', 10)).toBe('短文本');
  });

  it('应该处理刚好等于最大长度的文本', () => {
    expect(truncateText('12345', 5)).toBe('12345');
  });

  it('应该处理空字符串', () => {
    expect(truncateText('', 5)).toBe('');
  });
});

describe('getStatusColor', () => {
  describe('ownership 类型', () => {
    it('应该返回 green 对于已确权', () => {
      expect(getStatusColor('已确权', 'ownership')).toBe('green');
    });

    it('应该返回 red 对于未确权', () => {
      expect(getStatusColor('未确权', 'ownership')).toBe('red');
    });

    it('应该返回 orange 对于部分确权', () => {
      expect(getStatusColor('部分确权', 'ownership')).toBe('orange');
    });

    it('应该返回 default 对于未知状态', () => {
      expect(getStatusColor('未知', 'ownership')).toBe('default');
    });
  });

  describe('property 类型', () => {
    it('应该返回 blue 对于经营性', () => {
      expect(getStatusColor('经营性', 'property')).toBe('blue');
    });

    it('应该返回 default 对于非经营性', () => {
      expect(getStatusColor('非经营性', 'property')).toBe('default');
    });
  });

  describe('usage 类型', () => {
    it('应该返回 green 对于出租', () => {
      expect(getStatusColor('出租', 'usage')).toBe('green');
    });

    it('应该返回 red 对于空置', () => {
      expect(getStatusColor('空置', 'usage')).toBe('red');
    });

    it('应该返回 blue 对于自用', () => {
      expect(getStatusColor('自用', 'usage')).toBe('blue');
    });
  });

  describe('边界情况', () => {
    it('应该返回 default 对于 undefined', () => {
      expect(getStatusColor(undefined, 'ownership')).toBe('default');
    });

    it('应该返回 default 对于空字符串', () => {
      expect(getStatusColor('', 'usage')).toBe('default');
    });
  });
});

describe('calculateOccupancyRate', () => {
  it('应该计算出租率', () => {
    expect(calculateOccupancyRate(800, 1000)).toBe(80);
  });

  it('应该处理字符串输入', () => {
    expect(calculateOccupancyRate('800', '1000')).toBe(80);
  });

  it('应该返回 0 当已出租面积为 0', () => {
    expect(calculateOccupancyRate(0, 1000)).toBe(0);
  });

  it('应该返回 0 当可出租面积为 0', () => {
    expect(calculateOccupancyRate(800, 0)).toBe(0);
  });

  it('应该返回 0 当值为 null', () => {
    expect(calculateOccupancyRate(null, 1000)).toBe(0);
  });

  it('应该返回 0 当值为 undefined', () => {
    expect(calculateOccupancyRate(undefined, 1000)).toBe(0);
  });

  it('应该返回 0 当值为非数字字符串', () => {
    expect(calculateOccupancyRate('abc', 1000)).toBe(0);
  });
});

describe('isValidNumber', () => {
  it('应该返回 true 对于有效数字', () => {
    expect(isValidNumber(123)).toBe(true);
  });

  it('应该返回 true 对于数字字符串', () => {
    expect(isValidNumber('123.45')).toBe(true);
  });

  it('应该返回 false 对于 NaN', () => {
    expect(isValidNumber(NaN)).toBe(false);
  });

  it('应该返回 false 对于 Infinity', () => {
    expect(isValidNumber(Infinity)).toBe(false);
  });

  it('应该返回 false 对于非数字字符串', () => {
    expect(isValidNumber('abc')).toBe(false);
  });
});

describe('safeNumber', () => {
  it('应该返回有效数字', () => {
    expect(safeNumber(123)).toBe(123);
  });

  it('应该解析数字字符串', () => {
    expect(safeNumber('123.45')).toBe(123.45);
  });

  it('应该返回默认值对于无效输入', () => {
    expect(safeNumber('abc')).toBe(0);
  });

  it('应该返回自定义默认值', () => {
    expect(safeNumber('abc', -1)).toBe(-1);
  });

  it('应该处理 null', () => {
    expect(safeNumber(null)).toBe(0);
  });

  it('应该处理 undefined', () => {
    expect(safeNumber(undefined)).toBe(0);
  });
});
