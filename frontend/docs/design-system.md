# 设计系统规范

**版本**: 1.0.0
**最后更新**: 2026-02-06
**状态**: ✅ 活跃维护

---

## 概述

本设计系统为土地物业资产管理系统提供统一的视觉设计语言，确保所有组件和页面的一致性、可访问性和可维护性。

### 核心原则

1. **一致性**: 统一的设计语言，避免随意变化
2. **可访问性**: 符合 WCAG 2.1 AA 标准
3. **响应式**: 适配不同设备和屏幕尺寸
4. **性能**: 轻量级设计，优化加载速度
5. **可维护性**: 使用设计 Token，便于主题切换

---

## 1. 颜色系统

### 1.1 主色调（Primary Colors）

基于 Ant Design 的蓝色系，传达专业、可信赖的品牌形象。

| Token | 值 | 用途 |
|-------|---|------|
| `--color-primary` | `#1677ff` | 主按钮、链接、强调元素 |
| `--color-primary-hover` | `#4096ff` | 主按钮悬停状态 |
| `--color-primary-active` | `#0958d9` | 主按钮激活状态 |
| `--color-primary-light` | `#e6f4ff` | 浅色背景、徽章背景 |

**使用场景**:
```tsx
<Button type="primary">提交</Button>
<a href="...">查看详情</a>
<Tag color="blue">新功能</Tag>
```

### 1.2 辅助色（Secondary Colors）

用于区分主要操作和次要操作。

| Token | 值 | 用途 |
|-------|---|------|
| `--color-secondary` | `#0ea5e9` | 次要按钮、辅助链接 |
| `--color-secondary-hover` | `#38bdf8` | 悬停状态 |
| `--color-secondary-active` | `#0284c7` | 激活状态 |

### 1.3 语义色（Semantic Colors）

用于状态指示和反馈。

| 颜色 | Token | 值 | 用途 |
|------|-------|---|------|
| **成功** | `--color-success` | `#52c41a` | 成功提示、确认操作 |
| | `--color-success-light` | `#f6ffed` | 成功背景色 |
| **警告** | `--color-warning` | `#faad14` | 警告提示、注意事项 |
| | `--color-warning-light` | `#fffbe6` | 警告背景色 |
| **错误** | `--color-error` | `#ff4d4f` | 错误提示、删除操作 |
| | `--color-error-light` | `#fff2f0` | 错误背景色 |
| **信息** | `--color-info` | `#1890ff` | 信息提示 |
| | `--color-info-light` | `#e6f7ff` | 信息背景色 |

### 1.4 中性色（Neutral Colors）

用于文本、边框、背景。

| Token | 值 | 用途 | 对比度 |
|-------|---|------|--------|
| `--color-text-primary` | `#262626` | 主要文本（标题、正文） | 12.6:1 ✅ |
| `--color-text-secondary` | `#595959` | 次要文本（描述、说明） | 7:1 ✅ |
| `--color-text-tertiary` | `#8c8c8c` | 辅助文本（占位符、禁用） | 4.6:1 ✅ |
| `--color-text-quaternary` | `#bfbfbf` | 占位符文本 | 2.8:1 ⚠️ 仅用于纯装饰 |

**背景色**:
| Token | 值 | 用途 |
|-------|---|------|
| `--color-bg-primary` | `#ffffff` | 主背景（卡片、模态框） |
| `--color-bg-secondary` | `#fafafa` | 次要背景（页面背景） |
| `--color-bg-tertiary` | `#f5f5f5` | 三级背景（禁用区域） |
| `--color-bg-quaternary` | `#f0f0f0` | 四级背景（分隔区域） |

**边框色**:
| Token | 值 | 用途 |
|-------|---|------|
| `--color-border` | `#d9d9d9` | 标准边框 |
| `--color-border-light` | `#f0f0f0` | 浅色边框 |
| `--color-border-dark` | `#bfbfbf` | 深色边框 |

### 1.5 颜色使用原则

#### ✅ 正确使用
```tsx
// 使用 CSS 变量
<div style={{ color: 'var(--color-text-primary)' }}>
  主要文本
</div>

<div style={{ backgroundColor: 'var(--color-error)' }}>
  错误提示
</div>
```

#### ❌ 错误使用
```tsx
// 不要硬编码颜色值
<div style={{ color: '#262626' }}> // ❌
<div style={{ backgroundColor: '#ff4d4f' }}> // ❌
```

### 1.6 可访问性对比度要求

所有文本必须符合 WCAG 2.1 AA 标准：
- **正常文本**: 对比度 ≥ 4.5:1
- **大文本（18px+ 或 14px+ 粗体）**: 对比度 ≥ 3:1
- **UI 组件**: 对比度 ≥ 3:1

**工具推荐**:
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- Chrome DevTools Lighthouse

---

## 2. 字体系统

### 2.1 字体家族

```css
--font-family-base: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

**字体栈说明**:
1. `Inter` - 现代可选字体（需加载）
2. `-apple-system` - macOS/iOS 系统字体
3. `BlinkMacSystemFont` - Chrome macOS 字体
4. `Segoe UI` - Windows 10+ 字体
5. `Roboto` - Android 字体
6. `sans-serif` - 后备无衬线字体

### 2.2 字号（Font Size）

| Token | 值 | 用途 |
|-------|---|------|
| `--font-size-xs` | `12px` | 极小文本（标签、角标） |
| `--font-size-sm` | `13px` | 小文本（辅助信息） |
| `--font-size-base` | `14px` | 基础文本（正文） |
| `--font-size-lg` | `16px` | 大文本（重要内容） |
| `--font-size-xl` | `18px` | 小标题（卡片标题） |
| `--font-size-xxl` | `20px` | 中标题（区块标题） |
| `--font-size-xxxl` | `24px` | 大标题（页面标题） |

**响应式字号**:
```css
/* 移动端最小字体 */
body {
  font-size: 16px; /* 移动端最小可读字号 */
}

@media (min-width: 768px) {
  body {
    font-size: 14px; /* 桌面端可稍小 */
  }
}
```

### 2.3 字重（Font Weight）

| Token | 值 | 用途 |
|-------|---|------|
| `--font-weight-normal` | `400` | 常规文本 |
| `--font-weight-medium` | `500` | 中等文本（强调） |
| `--font-weight-semibold` | `600` | 半粗文本（小标题） |
| `--font-weight-bold` | `700` | 粗体（大标题） |

### 2.4 行高（Line Height）

| Token | 值 | 用途 |
|-------|---|------|
| `--line-height-tight` | `1.25` | 紧凑行高（标题） |
| `--line-height-base` | `1.5` | 基础行高（正文） |
| `--line-height-loose` | `1.75` | 宽松行高（长文本） |

### 2.5 排版示例

```tsx
// 页面标题
<h1 style={{ fontSize: 'var(--font-size-xxxl)', fontWeight: 'var(--font-weight-bold)' }}>
  资产列表
</h1>

// 卡片标题
<h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)' }}>
  物业信息
</h2>

// 正文
<p style={{ fontSize: 'var(--font-size-base)', lineHeight: 'var(--line-height-base)' }}>
  这是一个资产管理系统...
</p>
```

---

## 3. 间距系统

### 3.1 间距级别（Spacing Scale）

基于 4px 基础单位的倍数系统。

| Token | 值 | 用途 |
|-------|---|------|
| `--spacing-xs` | `4px` | 极小间距（图标内边距） |
| `--spacing-sm` | `8px` | 小间距（相关元素之间） |
| `--spacing-md` | `12px` | 中等间距（表单项之间） |
| `--spacing-lg` | `16px` | 大间距（卡片内边距） |
| `--spacing-xl` | `24px` | 超大间距（区块之间） |
| `--spacing-xxl` | `32px` | 极大间距（页面级别） |
| `--spacing-xxxl` | `48px` | 特大间距（章节之间） |

### 3.2 间距使用指南

#### 组件内边距（Padding）
```tsx
// 紧凑按钮
<Button style={{ padding: 'var(--spacing-sm) var(--spacing-md)' }}>
  确认
</Button>

// 卡片内边距
<Card style={{ padding: 'var(--spacing-lg)' }}>
  内容
</Card>

// 页面内边距
<div style={{ padding: 'var(--spacing-xl)' }}>
  页面内容
</div>
```

#### 组件外边距（Margin）
```tsx
// 表单项之间
<Form.Item style={{ marginBottom: 'var(--spacing-md)' }}>
  {/* ... */}
</Form.Item>

// 卡片之间
<Card style={{ marginBottom: 'var(--spacing-xl)' }}>
  {/* ... */}
</Card>
```

### 3.3 响应式间距

```css
/* 使用 clamp() 实现流畅响应式 */
.pageContainerResponsive {
  padding: clamp(12px, 2vw, 24px);
}
```

---

## 4. 组件规范

### 4.1 按钮（Button）

#### 尺寸规范
| 类型 | 高度 | 内边距 | 字号 |
|------|-----|--------|------|
| Small | `32px` | `8px 16px` | `13px` |
| Medium | `36px` | `8px 20px` | `14px` |
| Large | `40px` | `12px 24px` | `16px` |

#### 类型使用
```tsx
// 主要操作
<Button type="primary">提交</Button>

// 次要操作
<Button>取消</Button>

// 危险操作
<Button danger>删除</Button>

// 图标按钮
<Button icon={<PlusOutlined />}>新建</Button>
```

### 4.2 表单（Form）

#### 表单项布局
```tsx
<Form.Item
  label="物业名称"
  name="property_name"
  style={{ marginBottom: 'var(--spacing-md)' }}
  rules={[{ required: true, message: '请输入物业名称' }]}
>
  <Input placeholder="请输入物业名称" />
</Form.Item>
```

#### 表单内边距
- 表单容器: `var(--spacing-xl)`
- 表单项间距: `var(--spacing-md)`
- 标签底部间距: `var(--spacing-xs)`

### 4.3 卡片（Card）

#### 标准卡片
```tsx
<Card
  title="物业信息"
  style={{
    padding: 'var(--spacing-lg)',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-sm)',
  }}
>
  内容
</Card>
```

#### 卡片变体
| 类型 | 内边距 | 阴影 | 圆角 |
|------|--------|------|------|
| Compact | `var(--spacing-md)` | `var(--shadow-sm)` | `var(--radius-sm)` |
| Standard | `var(--spacing-lg)` | `var(--shadow-sm)` | `var(--radius-md)` |
| Spacious | `var(--spacing-xl)` | `var(--shadow-md)` | `var(--radius-lg)` |

### 4.4 表格（Table）

#### 表格规范
```tsx
<Table
  columns={columns}
  dataSource={data}
  size="middle"
  bordered
  sticky={{ offsetHeader: 64 }}
  scroll={{ x: 2000, y: 600 }}
  style={{
    fontSize: 'var(--font-size-base)',
  }}
/>
```

#### 单元格内边距
| 类型 | 垂直 | 水平 |
|------|-----|------|
| Small | `12px` | `12px` |
| Medium | `16px` | `16px` |

### 4.5 模态框（Modal）

#### 尺寸规范
| 类型 | 宽度 | 用途 |
|------|-----|------|
| Small | `520px` | 确认对话框 |
| Medium | `720px` | 表单对话框 |
| Large | `920px` | 详情展示 |

```tsx
<Modal
  title="创建资产"
  width={720}
  open={visible}
  onOk={handleOk}
  onCancel={handleCancel}
>
  内容
</Modal>
```

---

## 5. 响应式设计

### 5.1 断点系统（Breakpoints）

| Token | 值 | 设备 | 目标 |
|-------|---|------|------|
| `--breakpoint-xs` | `576px` | 小型手机 | 竖屏手机 |
| `--breakpoint-sm` | `768px` | 平板 | 横屏手机/小平板 |
| `--breakpoint-md` | `992px` | 桌面 | 平板/小桌面 |
| `--breakpoint-lg` | `1200px` | 大桌面 | 标准桌面 |
| `--breakpoint-xl` | `1400px` | 超大桌面 | 大屏幕 |
| `--breakpoint-xxl` | `1600px` | 4K 屏幕 | 超大屏幕 |

### 5.2 响应式策略

#### 移动优先
```tsx
// 默认移动端样式
<div className="card">...</div>

// 桌面端覆盖
@media (min-width: 768px) {
  .card {
    padding: var(--spacing-lg);
  }
}
```

#### 隐藏/显示元素
```tsx
// 使用 Ant Design Grid
<Row>
  <Col xs={24} md={12} lg={8}>
    移动端全宽，桌面端 1/2 宽
  </Col>
</Row>

// 使用响应式工具类
<xs className="hidden-md">仅移动端显示</xs>
<md className="hidden-xs">仅桌面端显示</md>
```

### 5.3 触摸目标规范

**最小尺寸**: 44px × 44px（WCAG 2.1 AAA）

```tsx
// ❌ 触摸目标过小
<IconButton size="small" icon={<EditIcon />} />

// ✅ 符合触摸标准
<IconButton
  size="large"
  icon={<EditIcon />}
  style={{ minWidth: 44, minHeight: 44 }}
/>
```

---

## 6. 动画与过渡

### 6.1 时长规范（Duration）

| Token | 值 | 用途 |
|-------|---|------|
| `--transition-instant` | `100ms` | 瞬时反馈（hover） |
| `--transition-fast` | `150ms` | 快速过渡（标准交互） |
| `--transition-base` | `200ms` | 基础过渡（淡入淡出） |
| `--transition-slow` | `300ms` | 慢速过渡（复杂动画） |
| `--transition-slower` | `500ms` | 超慢过渡（布局变化） |

### 6.2 缓动函数（Easing）

所有过渡统一使用 Material Design 的缓动函数：
```css
cubic-bezier(0.4, 0, 0.2, 1)
```

### 6.3 使用示例

```tsx
// 按钮悬停
<Button
  style={{
    transition: `all var(--transition-fast) cubic-bezier(0.4, 0, 0.2, 1)`,
  }}
>
  悬停我
</Button>

// 模态框淡入
<Modal
  style={{
    transition: `opacity var(--transition-base) cubic-bezier(0.4, 0, 0.2, 1)`,
  }}
>
  内容
</Modal>
```

### 6.4 减少动画（Reduced Motion）

系统已支持 `prefers-reduced-motion`，自动为敏感用户关闭动画：

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 7. 圆角与阴影

### 7.1 圆角（Border Radius）

| Token | 值 | 用途 |
|-------|---|------|
| `--radius-sm` | `4px` | 小圆角（按钮、输入框） |
| `--radius-md` | `8px` | 中圆角（卡片） |
| `--radius-lg` | `12px` | 大圆角（模态框） |
| `--radius-xl` | `16px` | 超大圆角（特殊卡片） |

### 7.2 阴影（Shadows）

| Token | 值 | 用途 |
|-------|---|------|
| `--shadow-sm` | `0 2px 4px rgba(0, 0, 0, 0.08)` | 轻微阴影（卡片） |
| `--shadow-md` | `0 4px 12px rgba(0, 0, 0, 0.1)` | 中等阴影（悬浮卡片） |
| `--shadow-lg` | `0 8px 24px rgba(0, 0, 0, 0.12)` | 大阴影（下拉菜单） |
| `--shadow-xl` | `0 20px 60px rgba(0, 0, 0, 0.15)` | 超大阴影（模态框） |

---

## 8. 层级管理（Z-Index）

| Token | 值 | 用途 |
|-------|---|------|
| `--z-index-dropdown` | `1000` | 下拉菜单 |
| `--z-index-sticky` | `1020` | 固定头部 |
| `--z-index-fixed` | `1030` | 固定侧边栏 |
| `--z-index-modal-backdrop` | `1040` | 模态框背景 |
| `--z-index-modal` | `1050` | 模态框内容 |
| `--z-index-popover` | `1060` | 气泡卡片 |
| `--z-index-tooltip` | `1070` | 工具提示 |

---

## 9. 可访问性规范

### 9.1 焦点样式（Focus Styles）

所有交互元素必须有清晰的焦点指示器：

```css
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  border-radius: 4px;
}
```

### 9.2 ARIA 标签

#### 按钮标签
```tsx
// 图标按钮必须有 aria-label
<IconButton
  icon={<EditIcon />}
  aria-label="编辑"
  title="编辑"
/>
```

#### 表单标签
```tsx
<Form.Item
  label="物业名称"
  aria-required="true"
>
  <Input
    aria-label="物业名称输入框"
    aria-describedby="property-name-help"
  />
</Form.Item>
```

#### 加载状态
```tsx
<div aria-busy="true" aria-live="polite">
  <Spin />
  加载中...
</div>
```

### 9.3 键盘导航

确保所有交互元素都可以通过键盘访问：
- `Tab` - 前进焦点
- `Shift + Tab` - 后退焦点
- `Enter` / `Space` - 激活按钮/链接
- `Escape` - 关闭模态框/下拉菜单

---

## 10. 深色模式

### 10.1 深色模式颜色

系统已支持深色模式，颜色自动适配：

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-text-primary: #ffffff;
    --color-text-secondary: rgba(255, 255, 255, 0.85);
    --color-bg-primary: #000000;
    --color-bg-secondary: #141414;
    --color-border: #434343;
  }
}
```

### 10.2 注意事项

- 保持足够对比度（4.5:1）
- 避免纯黑色（#000000）作为大面积背景
- 调整阴影效果（深色模式下阴影更明显）
- 优化图片显示（降低亮度）

---

## 11. 使用指南

### 11.1 引入方式

```tsx
// CSS 变量自动全局可用
<div style={{ color: 'var(--color-primary)' }}>
  主色文本
</div>
```

### 11.2 自定义主题

如需自定义设计 Token，修改 `frontend/src/styles/variables.css`：

```css
:root {
  --color-primary: #your-color;
  --font-size-base: 15px;
  /* ... */
}
```

### 11.3 添加新 Token

遵循命名规范：
- 颜色: `--color-{category}-{variant}`
- 间距: `--spacing-{size}`
- 字体: `--font-{property}-{variant}`
- 阴影: `--shadow-{size}`
- 圆角: `--radius-{size}`

---

## 12. 常见问题

### Q: 为什么不要硬编码颜色值？
A: 硬编码值破坏主题一致性，难以维护。使用 CSS 变量可以：
- 统一设计语言
- 轻松切换主题
- 减少重复代码

### Q: 间距为什么使用 4px 基础单位？
A: 4px 可以被 2、3、4 整除，提供足够的灵活性，同时保持一致性。

### Q: 如何确保颜色对比度符合标准？
A: 使用 WebAIM Contrast Checker 或 Chrome DevTools Lighthouse 检测。

### Q: 响应式间距如何实现？
A: 使用 `clamp(min, preferred, max)` 函数实现流畅响应式。

---

## 13. 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-02-06 | 初始版本，基于 Ant Design 6 |

---

## 14. 参考资源

- [Ant Design 设计规范](https://ant.design/docs/spec/introduce)
- [Material Design](https://material.io/design)
- [WCAG 2.1 指南](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM 对比度检查器](https://webaim.org/resources/contrastchecker/)

---

**维护者**: 前端开发团队
**反馈**: 如有问题或建议，请提交 Issue 或 PR
