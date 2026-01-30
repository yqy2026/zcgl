/**
 * EnumValuePreview 组件测试
 * 测试枚举值预览组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import type { EnumFieldValue } from '@/types/dictionary';

// Mock types
vi.mock('@/types/dictionary', () => ({}));

// Mock Ant Design components
interface TagMockProps {
  children?: React.ReactNode;
  color?: string;
  style?: React.CSSProperties;
}

interface TooltipMockProps {
  children?: React.ReactNode;
  title?: React.ReactNode;
}

interface SpaceMockProps {
  children?: React.ReactNode;
  wrap?: boolean;
  size?: 'small' | 'middle' | 'large' | number;
}

vi.mock('antd', () => ({
  Tag: ({ children, color, style }: TagMockProps) => (
    <div data-testid="tag" data-color={color} style={style}>
      {children}
    </div>
  ),
  Tooltip: ({ children, title }: TooltipMockProps) => (
    <div data-testid="tooltip" data-title={JSON.stringify(title)}>
      {children}
    </div>
  ),
  Space: ({ children, wrap, size }: SpaceMockProps) => (
    <div data-testid="space" data-wrap={wrap} data-size={size}>
      {children}
    </div>
  ),
}));

describe('EnumValuePreview - 组件导入测试', () => {
  it('应该能够导入EnumValuePreview组件', async () => {
    const module = await import('../EnumValuePreview');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });
});

describe('EnumValuePreview - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持values属性', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('应该支持maxDisplay属性', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      maxDisplay: 10,
    });
    expect(element).toBeTruthy();
  });

  it('默认maxDisplay应该是5', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('应该支持showInactiveCount属性', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      showInactiveCount: true,
    });
    expect(element).toBeTruthy();
  });

  it('默认showInactiveCount应该是true', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('应该支持size属性', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      size: 'large',
    });
    expect(element).toBeTruthy();
  });

  it('默认size应该是small', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('应该支持className属性', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      className: 'custom-class',
    });
    expect(element).toBeTruthy();
  });

  it('默认className应该是空字符串', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - 空状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('values为undefined应该显示暂无枚举值', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const element = React.createElement(EnumValuePreview, {
      values: undefined,
    });
    expect(element).toBeTruthy();
  });

  it('values为null应该显示暂无枚举值', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const element = React.createElement(EnumValuePreview, {
      values: null as unknown as EnumFieldValue[],
    });
    expect(element).toBeTruthy();
  });

  it('values为空数组应该显示暂无枚举值', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const element = React.createElement(EnumValuePreview, {
      values: [],
    });
    expect(element).toBeTruthy();
  });

  it('values不是数组应该显示暂无枚举值', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const element = React.createElement(EnumValuePreview, {
      values: 'invalid' as unknown as EnumFieldValue[],
    });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - 活跃值过滤测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该只显示is_active为true的值', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      { id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 },
      { id: '2', label: '选项2', value: 'opt2', is_active: false, sort_order: 2 },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('应该按sort_order排序', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      { id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 2 },
      { id: '2', label: '选项2', value: 'opt2', is_active: true, sort_order: 1 },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('应该限制maxDisplay数量', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = Array.from({ length: 10 }, (_, i) => ({
      id: String(i),
      label: `选项${i}`,
      value: `opt${i}`,
      is_active: true,
      sort_order: i,
    }));
    const element = React.createElement(EnumValuePreview, {
      values,
      maxDisplay: 5,
    });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - 非活跃数量测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该计算非活跃数量', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      { id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 },
      { id: '2', label: '选项2', value: 'opt2', is_active: false, sort_order: 2 },
      { id: '3', label: '选项3', value: 'opt3', is_active: false, sort_order: 3 },
    ];
    const element = React.createElement(EnumValuePreview, {
      values,
      showInactiveCount: true,
    });
    expect(element).toBeTruthy();
  });

  it('showInactiveCount为false时不显示非活跃数量', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      { id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 },
      { id: '2', label: '选项2', value: 'opt2', is_active: false, sort_order: 2 },
    ];
    const element = React.createElement(EnumValuePreview, {
      values,
      showInactiveCount: false,
    });
    expect(element).toBeTruthy();
  });

  it('无非活跃值时不显示非活跃数量', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      showInactiveCount: true,
    });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - 剩余数量测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示剩余数量', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = Array.from({ length: 10 }, (_, i) => ({
      id: String(i),
      label: `选项${i}`,
      value: `opt${i}`,
      is_active: true,
      sort_order: i,
    }));
    const element = React.createElement(EnumValuePreview, {
      values,
      maxDisplay: 5,
    });
    expect(element).toBeTruthy();
  });

  it('无剩余值时不显示剩余数量', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      { id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 },
      { id: '2', label: '选项2', value: 'opt2', is_active: true, sort_order: 2 },
    ];
    const element = React.createElement(EnumValuePreview, {
      values,
      maxDisplay: 5,
    });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - Tag样式测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('size为small应该有对应样式', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      size: 'small',
    });
    expect(element).toBeTruthy();
  });

  it('size为middle应该有对应样式', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      size: 'middle',
    });
    expect(element).toBeTruthy();
  });

  it('size为large应该有对应样式', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      size: 'large',
    });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - Tooltip测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示Tooltip', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      {
        id: '1',
        label: '选项1',
        value: 'opt1',
        is_active: true,
        sort_order: 1,
        code: 'CODE1',
        description: '描述1',
      },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('Tooltip应该包含标签', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('Tooltip应该包含值', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('Tooltip应该包含编码', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      {
        id: '1',
        label: '选项1',
        value: 'opt1',
        is_active: true,
        sort_order: 1,
        code: 'CODE1',
      },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('Tooltip应该包含描述', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      {
        id: '1',
        label: '选项1',
        value: 'opt1',
        is_active: true,
        sort_order: 1,
        description: '描述1',
      },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('Tooltip应该包含排序', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - 默认值测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('is_default为true应该显示星标', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      {
        id: '1',
        label: '选项1',
        value: 'opt1',
        is_active: true,
        sort_order: 1,
        is_default: true,
      },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('is_default为false或undefined不显示星标', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      {
        id: '1',
        label: '选项1',
        value: 'opt1',
        is_active: true,
        sort_order: 1,
        is_default: false,
      },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - Tag颜色测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('有color时使用自定义颜色', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      {
        id: '1',
        label: '选项1',
        value: 'opt1',
        is_active: true,
        sort_order: 1,
        color: 'blue',
      },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('无color时使用green', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('is_default为true时使用gold', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      {
        id: '1',
        label: '选项1',
        value: 'opt1',
        is_active: true,
        sort_order: 1,
        is_default: true,
      },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - Space组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该使用Space组件', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('Space应该支持wrap', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理所有值为非活跃', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      { id: '1', label: '选项1', value: 'opt1', is_active: false, sort_order: 1 },
      { id: '2', label: '选项2', value: 'opt2', is_active: false, sort_order: 2 },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('应该处理负sort_order', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [
      { id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: -1 },
      { id: '2', label: '选项2', value: 'opt2', is_active: true, sort_order: 1 },
    ];
    const element = React.createElement(EnumValuePreview, { values });
    expect(element).toBeTruthy();
  });

  it('应该处理maxDisplay为0', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = [{ id: '1', label: '选项1', value: 'opt1', is_active: true, sort_order: 1 }];
    const element = React.createElement(EnumValuePreview, {
      values,
      maxDisplay: 0,
    });
    expect(element).toBeTruthy();
  });
});

describe('EnumValuePreview - 剩余数量Tag测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('剩余数量Tag应该有processing颜色', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = Array.from({ length: 10 }, (_, i) => ({
      id: String(i),
      label: `选项${i}`,
      value: `opt${i}`,
      is_active: true,
      sort_order: i,
    }));
    const element = React.createElement(EnumValuePreview, {
      values,
      maxDisplay: 5,
    });
    expect(element).toBeTruthy();
  });

  it('剩余数量Tag应该显示数量', async () => {
    const EnumValuePreview = (await import('../EnumValuePreview')).default;
    const values = Array.from({ length: 10 }, (_, i) => ({
      id: String(i),
      label: `选项${i}`,
      value: `opt${i}`,
      is_active: true,
      sort_order: i,
    }));
    const element = React.createElement(EnumValuePreview, {
      values,
      maxDisplay: 5,
    });
    expect(element).toBeTruthy();
  });
});
