# 可访问性实施指南

**版本**: 1.0.0
**最后更新**: 2026-02-06
**目标**: 符合 WCAG 2.1 AA 标准

---

## 目录

1. [快速开始](#快速开始)
2. [工具函数使用](#工具函数使用)
3. [组件可访问性](#组件可访问性)
4. [检查清单](#检查清单)
5. [测试方法](#测试方法)
6. [常见问题](#常见问题)

---

## 快速开始

### 什么是可访问性？

可访问性（Accessibility / A11y）确保**所有用户**，包括使用辅助技术的用户，都能有效使用您的应用。

### 为什么重要？

1. **法律合规**: 符合《无障碍环境建设条例》
2. **用户群体**: 约 15% 的人口有某种形式的残疾
3. **更好的 UX**: 可访问性实践改善所有人的体验
4. **SEO 优势**: 搜索引擎偏好可访问的网站

### WCAG 2.1 AA 标准四大原则

| 原则 | 英文 | 说明 |
|------|------|------|
| 可感知 | Perceivable | 用户必须能够感知信息和界面 |
| 可操作 | Operable | 用户必须能够操作界面 |
| 可理解 | Understandable | 用户必须能够理解内容和操作 |
| 健壮性 | Robust | 内容必须足够健壮，可与各种辅助技术兼容 |

---

## 工具函数使用

### 1. generateAriaLabel - 生成 ARIA 标签

为图标按钮生成描述性的 ARIA 标签。

```tsx
import { generateAriaLabel } from '@/utils/accessibility';

// ❌ 错误 - 图标按钮没有标签
<IconButton icon={<EditIcon />} />

// ✅ 正确 - 使用 generateAriaLabel
<IconButton
  icon={<EditIcon />}
  aria-label={generateAriaLabel('edit', '资产')}
  title="编辑资产"
/>

// 示例输出: "编辑资产"
```

### 2. announceToScreenReader - 屏幕阅读器通知

向屏幕阅读器宣布重要状态变化。

```tsx
import { announceToScreenReader } from '@/utils/accessibility';

const handleSubmit = async () => {
  try {
    await createAsset(data);
    // ✅ 通知成功
    announceToScreenReader('资产创建成功', 'polite');
  } catch (error) {
    // ✅ 通知错误
    announceToScreenReader('资产创建失败，请重试', 'assertive');
  }
};

// 上传进度通知
const handleUploadProgress = (percent: number) => {
  announceToScreenReader(`上传进度 ${percent}%`, 'polite');
};
```

### 3. generateId - 生成唯一 ID

为 ARIA 属性生成唯一的元素 ID。

```tsx
import { generateId } from '@/utils/accessibility';

const FormField: React.FC = () => {
  const fieldId = generateId('field');

  return (
    <>
      <label htmlFor={fieldId}>物业名称</label>
      <input id={fieldId} type="text" />
    </>
  );
};
```

### 4. getIconButtonProps - 获取图标按钮属性

一次性生成图标按钮所需的所有可访问性属性。

```tsx
import { getIconButtonProps } from '@/utils/accessibility';

const ActionButtons: React.FC = () => {
  return (
    <>
      <Button
        icon={<EditOutlined />}
        {...getIconButtonProps('edit', '资产')}
      />

      <Button
        icon={<DeleteOutlined />}
        {...getIconButtonProps('delete', '资产')}
        danger
      />
    </>
  );
};
```

### 5. generateFormFieldIds - 生成表单字段 ID

为表单字段生成所有相关 ID。

```tsx
import { generateFormFieldIds } from '@/utils/accessibility';

const FormField: React.FC<{ name: string }> = ({ name }) => {
  const ids = generateFormFieldIds(name);

  return (
    <Form.Item
      label={label}
      htmlFor={ids.inputId}
      help={description}
      validateStatus={error ? 'error' : ''}
    >
      <Input
        id={ids.inputId}
        aria-describedby={ids.descriptionId}
        aria-invalid={!!error}
        aria-errormessage={error ? ids.errorId : undefined}
      />
      {error && <span id={ids.errorId}>{error}</span>}
    </Form.Item>
  );
};
```

### 6. prefersReducedMotion - 检测动画偏好

检测用户是否偏好减少动画。

```tsx
import { prefersReducedMotion, getAccessibleDuration } from '@/utils/accessibility';

const AnimatedComponent: React.FC = () => {
  const duration = getAccessibleDuration(300);

  return (
    <div
      style={{
        transition: `all ${duration}ms ease-in-out`,
      }}
    >
      内容
    </div>
  );
};
```

---

## 组件可访问性

### 按钮（Button）

#### 基础按钮
```tsx
// ✅ 正确
<Button type="primary" onClick={handleClick}>
  提交
</Button>

// ✅ 图标按钮必须有标签
<Button
  icon={<EditOutlined />}
  aria-label="编辑"
  title="编辑"
/>
```

#### 禁用状态
```tsx
// ✅ 正确 - 使用 disabled 属性
<Button disabled onClick={handleClick}>
  禁用按钮
</Button>

// ❌ 错误 - 不要仅依靠样式禁用
<Button style={{ opacity: 0.5 }} onClick={handleClick}>
  {/* 用户仍可以点击！ */}
</Button>
```

### 表单（Form）

#### 标签关联
```tsx
// ✅ 正确 - 使用 htmlFor 关联
<Form.Item label="物业名称" name="property_name">
  <Input id="property_name" />
</Form.Item>

// ❌ 错误 - 没有关联
<Form.Item label="物业名称">
  <Input />
</Form.Item>
```

#### 必填字段
```tsx
// ✅ 正确 - 使用 aria-required
<Form.Item
  label="物业名称"
  name="property_name"
  rules={[{ required: true, message: '请输入物业名称' }]}
  aria-required="true"
>
  <Input aria-label="物业名称输入框" />
</Form.Item>
```

#### 错误消息
```tsx
// ✅ 正确 - 关联错误消息
<Form.Item
  validateStatus="error"
  help="请输入有效的物业名称"
>
  <Input
    aria-invalid="true"
    aria-errormessage="property-name-error"
  />
  <span id="property-name-error" role="alert">
    请输入有效的物业名称
  </span>
</Form.Item>
```

### 表格（Table）

#### 表格标题
```tsx
// ✅ 正确 - 添加 caption
<Table
  title="资产列表"
  columns={columns}
  dataSource={data}
  accessibility={{ caption: '资产列表表格' }}
/>
```

#### 排序指示器
```tsx
// ✅ 正确 - 使用 aria-sort
const columns = [
  {
    title: '物业名称',
    dataIndex: 'property_name',
    key: 'property_name',
    sorter: true,
    sortOrder: 'ascend',
    // 添加 aria-sort
    onHeaderCell: (column) => ({
      'aria-sort': column.sortOrder === 'ascend' ? 'ascending' : 'descending',
    }),
  },
];
```

### 模态框（Modal）

#### 焦点陷阱
```tsx
import { trapFocus } from '@/utils/accessibility';

const ModalComponent: React.FC = () => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (visible && modalRef.current) {
      // 陷阱焦点在模态框内
      const cleanup = trapFocus(modalRef.current);
      return cleanup;
    }
  }, [visible]);

  return (
    <Modal ref={modalRef} visible={visible} onClose={handleClose}>
      内容
    </Modal>
  );
};
```

#### ARIA 属性
```tsx
// ✅ 正确 - 完整的 ARIA 属性
<Modal
  title="创建资产"
  open={visible}
  onOk={handleOk}
  onCancel={handleCancel}
  role="dialog"
  aria-modal="true"
  aria-labelledby="modal-title"
  aria-describedby="modal-description"
>
  <h2 id="modal-title">创建资产</h2>
  <p id="modal-description">填写以下信息创建新资产</p>
  {/* 表单内容 */}
</Modal>
```

### 下拉菜单（Dropdown）

#### 键盘导航
```tsx
// ✅ 确保 Ant Design Dropdown 支持键盘导航
<Dropdown
  menu={{
    items,
    // 键盘导航自动支持
  }}
  trigger={['click']}
>
  <Button>操作</Button>
</Dropdown>
```

### 加载状态（Loading）

#### ARIA Live 区域
```tsx
// ✅ 正确 - 使用 aria-live
<div aria-live="polite" aria-busy={loading}>
  {loading ? <Spin /> : <Content />}
</div>
```

### 通知（Notification）

#### 自动通知
```tsx
import { announceToScreenReader } from '@/utils/accessibility';

const showNotification = (message: string, type: 'success' | 'error') => {
  notification[type]({
    message,
    // ✅ 同时通知屏幕阅读器
    onClose: () => announceToScreenReader(message, 'assertive'),
  });
};
```

---

## 检查清单

### 页面级检查

- [ ] **页面标题** - 每个页面有唯一的 `<title>`
- [ ] **语言属性** - `<html lang="zh-CN">`
- [ ] **跳过导航** - 提供"跳转到主内容"链接
- [ ] **焦点顺序** - Tab 顺序符合视觉顺序
- [ ] **页面结构** - 使用语义化 HTML（header, nav, main, footer）

### 组件级检查

#### 按钮
- [ ] 所有按钮有明确的文本或 `aria-label`
- [ ] 图标按钮有描述性标签
- [ ] 禁用状态使用 `disabled` 属性

#### 表单
- [ ] 所有输入框有关联的 `<label>`
- [ ] 必填字段有 `aria-required="true"`
- [ ] 错误消息关联到输入框（`aria-errormessage`）
- [ ] 表单提交有明确的反馈

#### 链接
- [ ] 链接文本描述明确（避免"点击这里"）
- [ ] 外部链接有明确指示
- [ ] 新窗口链接有 `aria-label` 或说明

#### 图片
- [ ] 所有图片有 `alt` 属性
- [ ] 装饰性图片使用 `alt=""`
- [ ] 复杂图片有详细描述

### 键盘导航

- [ ] **Tab 键** - 可以导航所有交互元素
- [ ] **Enter/Space** - 可以激活按钮和链接
- [ ] **Escape** - 可以关闭模态框和下拉菜单
- [ ] **方向键** - 可以在列表和表格中导航
- [ ] **焦点可见** - 焦点有清晰的视觉指示

### 颜色对比度

- [ ] **文本对比度** - 正常文本 ≥ 4.5:1
- [ ] **大文本对比度** - 18px+ 或 14px+ 粗体 ≥ 3:1
- [ ] **UI 组件** - 边框、焦点指示器 ≥ 3:1

**检查工具**:
- [Chrome DevTools Lighthouse](https://chrome.google.com/webstore/detail/lighthouse/blbmcpojkalnbkemiigbggpjnofkemgm)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [WAVE](https://wave.webaim.org/)

---

## 测试方法

### 1. 键盘导航测试

**目标**: 确保所有功能都可以仅使用键盘访问。

**步骤**:
1. 断开鼠标
2. 使用 `Tab` 键导航整个应用
3. 验证:
   - [ ] 焦点顺序合理
   - [ ] 所有交互元素可获得焦点
   - [ ] 焦点指示器清晰可见
   - [ ] `Enter`/`Space` 可以激活按钮
   - [ ] `Escape` 可以关闭模态框/下拉菜单
   - [ ] 方向键可以在列表/表格中导航

### 2. 屏幕阅读器测试

**工具**:
- **Windows**: [NVDA](https://www.nvaccess.org/)（免费）
- **macOS**: VoiceOver（内置）
- **Android**: TalkBack（内置）
- **iOS**: VoiceOver（内置）

**测试步骤**:
1. 打开屏幕阅读器
2. 导航到您的应用
3. 验证:
   - [ ] 页面标题被朗读
   - [ ] 按钮和链接有描述性标签
   - [ ] 表单字段有关联的标签
   - [ ] 错误消息被朗读
   - [ ] 状态变化被通知
   - [ ] 列表和表格结构清晰

### 3. 颜色对比度测试

**工具**:
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- Chrome DevTools Lighthouse

**步骤**:
1. 打开 Chrome DevTools
2. 运行 Lighthouse 审计
3. 检查 Accessibility 部分
4. 修复所有对比度问题

### 4. 缩放测试

**目标**: 确保应用在 200% 缩放下仍然可用。

**步骤**:
1. 浏览器缩放到 200%（Ctrl/Cmd + Plus）
2. 验证:
   - [ ] 没有水平滚动
   - [ ] 文本仍然可读
   - [ ] 没有内容被裁剪
   - [ ] 交互元素仍然可用

### 5. 自动化测试

#### axe-core 测试
```bash
pnpm add -D @axe-core/react jest-axe
```

```tsx
// __tests__/Accessibility.test.tsx
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

describe('Accessibility', () => {
  it('should not have accessibility violations', async () => {
    const { container } = render(<MyComponent />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

#### Lighthouse CI
```bash
# 安装 Lighthouse CI
pnpm add -D @lhci/cli

# 配置 lighthouserc.js
module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:5173'],
      numberOfRuns: 3,
    },
    assert: {
      preset: 'lighthouse:recommended',
      assertions: {
        'categories:accessibility': ['error', { minScore: 0.9 }],
      },
    },
  },
};
```

---

## 常见问题

### Q: 如何处理动态内容？

**A**: 使用 `aria-live` 区域。

```tsx
<div
  aria-live="polite"
  aria-atomic="true"
  role="status"
>
  {dynamicContent}
</div>
```

**优先级**:
- `polite` - 等待用户空闲后再通知（推荐）
- `assertive` - 立即中断用户（仅用于错误和警告）

### Q: 如何隐藏视觉元素但对屏幕阅读器可见？

**A**: 使用 `.sr-only` 类。

```tsx
<span className="sr-only">这是屏幕阅读器专用文本</span>
```

CSS:
```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

### Q: 如何处理模态框的焦点陷阱？

**A**: 使用 `trapFocus` 工具函数。

```tsx
import { trapFocus } from '@/utils/accessibility';

useEffect(() => {
  if (modalRef.current) {
    return trapFocus(modalRef.current);
  }
}, [visible]);
```

### Q: 如何为图标按钮生成标签？

**A**: 使用 `getIconButtonProps` 工具。

```tsx
import { getIconButtonProps } from '@/utils/accessibility';

<Button
  icon={<EditOutlined />}
  {...getIconButtonProps('edit', '资产')}
/>
```

### Q: 如何通知屏幕阅读器状态变化？

**A**: 使用 `announceToScreenReader` 工具。

```tsx
import { announceToScreenReader } from '@/utils/accessibility';

const handleSuccess = () => {
  announceToScreenReader('操作成功', 'polite');
};

const handleError = () => {
  announceToScreenReader('操作失败，请重试', 'assertive');
};
```

### Q: 如何测试颜色对比度？

**A**: 使用 WebAIM Contrast Checker 或 Lighthouse。

1. 访问 https://webaim.org/resources/contrastchecker/
2. 输入前景色和背景色
3. 检查对比度是否 ≥ 4.5:1

---

## 资源链接

### 工具
- [axe DevTools](https://www.deque.com/axe/devtools/) - Chrome 可访问性测试
- [WAVE](https://wave.webaim.org/) - 在线可访问性评估
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Chrome 内置审计
- [Color Contrast Analyzer](https://www.tpgi.com/color-contrast-checker/) - 桌面应用

### 文档
- [WCAG 2.1 快速参考](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA 实践指南](https://www.w3.org/WAI/ARIA/apg/)
- [MDN 可访问性](https://developer.mozilla.org/zh-CN/docs/Web/Accessibility)

### 屏幕��读器
- [NVDA](https://www.nvaccess.org/) - Windows（免费）
- [JAWS](https://www.freedomscientific.com/products/software/jaws/) - Windows（付费）
- [VoiceOver](https://www.apple.com/accessibility/voiceover/) - macOS/iOS（内置）
- [TalkBack](https://support.google.com/accessibility/android/answer/6283677) - Android（内置）

---

## 总结

可访问性不是"附加功能"，而是**必需的基础要求**。通过遵循本指南和使用提供的工具函数，您可以：

1. ✅ 符合法律要求
2. ✅ 扩大用户群体
3. ✅ 改善所有用户体验
4. ✅ 提升代码质量

**记住**: 可访问性设计**惠及所有用户**，而不仅仅是残障用户。

---

**维护者**: 前端开发团队
**反馈**: 如有问题或建议，请提交 Issue 或 PR
**版本**: 1.0.0 | 2026-02-06
