# 动画和过渡最佳实践指南

## 🎯 概述

本文档定义了项目中动画和过渡的标准规范，确保一致的用户体验和流畅的交互反馈。

## ⏱️ 标准过渡时长

我们采用 **Material Design** 的标准时长系统，所有过渡都使用统一的缓动函数。

### 定义 (位于 `src/styles/variables.css`)

```css
/* Transitions - Material Design inspired */
--transition-instant: 100ms cubic-bezier(0.4, 0, 0.2, 1);   /* 微交互 */
--transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);     /* 标准交互 */
--transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);     /* 基础动画 */
--transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1);     /* 复杂过渡 */
--transition-slower: 500ms cubic-bezier(0.4, 0, 0.2, 1);   /* 重大布局变化 */
```

### 使用场景

| 时长 | 用途 | 示例 |
|------|------|------|
| **100ms** | 瞬时反馈 | 按钮按下、复选框选中 |
| **150ms** ⭐ | 标准交互 | 链接hover、卡片展开、菜单项 |
| **200ms** | 基础动画 | 工具提示显示、面板淡入 |
| **300ms** | 复杂过渡 | 模态框打开、页面切换 |
| **500ms** | 重大变化 | 大型布局重排、复杂动画序列 |

⭐ **150ms 是我们的默认选择**

---

## 📐 缓动函数

### 标准缓动: `cubic-bezier(0.4, 0, 0.2, 1)`

这是Material Design的标准缓动曲线，提供：
- ✅ 快速启动 (0.4)
- ✅ 平滑减速 (0.2, 1)
- ✅ 自然的运动感觉

### 为什么不用 `ease`?

```css
/* ❌ 避免 */
transition: all 0.3s ease;

/* ✅ 推荐 */
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

**原因**: `ease` (cubic-bezier(0.25, 0.1, 0.25, 1)) 启动较慢，感觉不够灵敏。

---

## 💡 使用CSS变量

**永远使用CSS变量而非硬编码值**：

```tsx
/* ❌ 错误 - 硬编码 */
const style = {
  transition: 'all 0.2s ease'
};

/* ✅ 正确 - 使用CSS类 */
<div className="my-element" />

/* ✅ 正确 - 使用CSS变量 */
.myElement {
  transition: all var(--transition-fast);
}
```

### React中正确使用

```tsx
// ✅ 使用CSS模块/类名
import styles from './MyComponent.module.css';

<div className={styles.hoverable} />

// ✅ 使用CSS-in-JS库 (styled-components)
import styled from 'styled-components';

const HoverableDiv = styled.div`
  transition: all var(--transition-fast);
`;

// ❌ 避免内联样式（除非动态值必需）
<div style={{ transition: 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)' }}>
```

---

## 🎨 常见过渡模式

### 1. Hover状态 (最常见)

```css
/* 标准hover效果 */
.button {
  transition: all var(--transition-fast);
}

.button:hover {
  background: var(--color-primary-hover);
  transform: translateY(-2px);
}
```

### 2. 模态框/对话框

```css
/* 淡入 + 轻微缩放 */
.modal {
  opacity: 0;
  transform: scale(0.95);
  transition:
    opacity var(--transition-slow),
    transform var(--transition-slow);
}

.modal.open {
  opacity: 1;
  transform: scale(1);
}
```

### 3. 侧边栏/抽屉

```css
/* 滑动效果 */
.drawer {
  transform: translateX(-100%);
  transition: transform var(--transition-slow);
}

.drawer.open {
  transform: translateX(0);
}
```

### 4. 颜色变化

```css
/* 只过渡颜色属性 */
.link {
  color: var(--color-primary);
  transition: color var(--transition-fast);
}

.link:hover {
  color: var(--color-primary-hover);
}
```

---

## ⚠️ 常见错误

### ❌ 错误1: 过渡 `all`

```css
/* ❌ 过渡所有属性 - 性能差 */
.element {
  transition: all 0.3s;
}

/* ✅ 只过渡需要的属性 */
.element {
  transition:
    background var(--transition-fast),
    color var(--transition-fast);
}
```

### ❌ 错误2: 时长过长

```css
/* ❌ 太慢 - 用户感到卡顿 */
.button:hover {
  transition: all 1s;
}

/* ✅ 标准150ms */
.button:hover {
  transition: all var(--transition-fast);
}
```

### ❌ 错误3: 不一致的时长

```css
/* ❌ 同一页面使用不同时长 */
.button1 { transition: all 0.2s; }
.button2 { transition: all 0.3s; }
.button3 { transition: all 0.5s; }

/* ✅ 使用统一的CSS变量 */
.button1,
.button2,
.button3 {
  transition: all var(--transition-fast);
}
```

### ❌ 错误4: 忘记设置初始状态

```css
/* ❌ 只设置了hover状态 */
.button:hover {
  background: blue;
}

/* ✅ 同时设置初始和hover状态 */
.button {
  background: white;
  transition: background var(--transition-fast);
}

.button:hover {
  background: blue;
}
```

---

## 📱 响应式间距

使用 `clamp()` 函数实现流体间距：

### 标准类 (位于 `src/styles/common.css`)

```css
/* 页面容器 */
.pageContainerResponsive {
  padding: clamp(12px, 2vw, 24px);
}

/* 间距 */
.marginBottomResponsive {
  margin-bottom: clamp(8px, 1.5vw, 16px);
}

.paddingResponsive {
  padding: clamp(12px, 2vw, 24px);
}
```

### 使用示例

```tsx
/* ✅ 响应式padding */
<div className="pageContainerResponsive">
  内容自动适配移动端和桌面端
</div>

/* ✅ 响应式margin */
<Section className="marginBottomResponsive">
  子元素间距随视口调整
</Section>
```

### clamp() 参数说明

```css
clamp(MIN, PREFERRED, MAX)
```

- **MIN**: 最小值（移动端）
- **PREFERRED**: 首选值（基于viewport）
- **MAX**: 最大值（桌面端）

**示例**: `clamp(12px, 2vw, 24px)`
- 小屏幕 (375px): 12px
- 中等屏幕 (1024px): ~20px
- 大屏幕 (1920px): 24px

---

## 🚀 性能优化

### 1. 使用GPU加速属性

优先使用这些属性（触发GPU加速）：
- ✅ `transform`
- ✅ `opacity`
- ✅ `filter`

避免频繁动画这些属性（触发重排）：
- ❌ `width`, `height`
- ❌ `top`, `left`, `right`, `bottom`
- ❌ `margin`, `padding`

### 2. 减少重绘

```css
/* ❌ 多次触发重绘 */
.box {
  transition:
    width 0.3s,
    height 0.3s,
    background 0.3s;
}

/* ✅ 使用transform - GPU加速 */
.box {
  transition: transform 0.3s;
}

.box:hover {
  transform: scale(1.1);
}
```

### 3. 使用 `will-change` (谨慎)

```css
/* 仅在知道会动画时使用 */
.animatedElement {
  will-change: transform, opacity;
}

/* 动画结束后移除 */
.animatedElement.finished {
  will-change: auto;
}
```

**注意**: 不要滥用 `will-change`，它会消耗额外内存。

---

## ♿ 可访问性考虑

### 尊重用户的动画偏好

```css
/* 自动支持 prefers-reduced-motion (已包含在 global.css) */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 确保动画不是必需的

```tsx
/* ✅ 动画增强体验，但不影响功能 */
<div className="fade-in">
  内容动画淡入，但即使禁用动画也能正常显示
</div>
```

---

## 📋 检查清单

在提交代码前，确认：

- [ ] 使用了CSS变量 (`var(--transition-fast)`)
- [ ] 没有硬编码时长 (`0.2s`, `300ms`)
- [ ] Hover状态使用150ms
- [ ] 模态框/抽屉使用300ms
- [ ] 只过渡需要的属性，避免 `all`
- [ ] 复杂动画考虑GPU加速 (`transform`, `opacity`)
- [ ] 响应式间距使用 `clamp()`
- [ ] 测试了 `prefers-reduced-motion` 兼容性

---

## 🎓 学习资源

- [Material Design Motion](https://material.io/design/motion/)
- [MDN: CSS Transitions](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions)
- [web.dev: Animations](https://web.dev/animations-guide/)

---

## 🔄 迁移现有代码

### 批量查找需要更新的代码

```bash
# 查找硬编码的过渡时长
cd frontend/src
grep -r "transition.*0\.[0-9]" --include="*.css" --include="*.tsx"

# 查找使用 "ease" 的地方
grep -r "transition.*ease" --include="*.css"
```

### 替换模式

```css
/* 查找 */
transition: all 0.2s ease;
transition: all 0.3s ease;

/* 替换为 */
transition: all var(--transition-fast);
transition: all var(--transition-slow);
```

---

## 💬 常见问题

**Q: 为什么不能用 `transition: all`?**
A: `all` 会过渡所有可动画属性，包括你可能没想到的，导致性能问题和不必要的副作用。

**Q: 什么时候用 `transition-fast` vs `transition-slow`?**
A: 大多数交互用 `fast` (150ms)。只有模态框、抽屉等复杂UI用 `slow` (300ms)。

**Q: `clamp()` 在所有浏览器都支持吗?**
A: 现代浏览器都支持。IE不支持，但项目已不再支持IE。

**Q: 如何测试动画性能?**
A: 使用Chrome DevTools的Performance面板，记录帧率。目标是保持60fps。
