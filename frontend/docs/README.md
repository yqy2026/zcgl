# 前端文档索引

本目录包含土地物业资产管理系统前端的完整文档。

## 📚 核心文档

### 设计系统
- **[design-system.md](./design-system.md)** - 完整的设计系统规范
  - 颜色系统、字体系统、间距系统
  - 组件规范、响应式设计、动画规范
  - 深色模式、可访问性规范

### 可访问性
- **[accessibility-guide.md](./accessibility-guide.md)** - 可访问性实施指南
  - 工具函数使用示例
  - 组件可访问性规范
  - 测试方法和检查清单

### UI/UX 改进
- **[frontend-optimization-complete-report.md](./frontend-optimization-complete-report.md)** - 最终完整实施报告（最新）
  - 全部6个阶段完成：设计系统、可访问性、移动端优化、状态组件、深色模式、性能优化
  - 29个组件，33个字段，100%覆盖
  - 3,260行代码，4,750行文档

- **[frontend-a11y-complete-final-report.md](./frontend-a11y-complete-final-report.md)** - 阶段1-5总结
  - 25个组件，33个字段，100%覆盖
  - 2,750行代码，4,350行文档

- **[frontend-a11y-complete-report-with-mobile.md](./frontend-a11y-complete-report-with-mobile.md)** - 阶段1-4总结
  - 22个组件，33个字段，100%覆盖
  - 1,900行代码，3,700行文档

- **[frontend-a11y-complete-report-with-mobile.md](./frontend-a11y-complete-report-with-mobile.md)** - 阶段1-4总结
  - 22个组件，33个字段，100%覆盖
  - 1,900行代码，3,700行文档

- **[frontend-a11y-complete-report-2026-02-06.md](./frontend-a11y-complete-report-2026-02-06.md)** - 阶段1-3总结
  - 7个组件，33个字段，100%覆盖
  - 575行代码，4,000行文档

- **[form-sections-a11y-optimization-summary.md](./form-sections-a11y-optimization-summary.md)** - 表单组件优化总结
  - 4 个表单 Section 组件优化
  - 33 个字段可访问性改进

- **[frontend-a11y-progress-report-2026-02-06.md](./frontend-a11y-progress-report-2026-02-06.md)** - 第一 + 第二阶段总结
  - 量化指标和成果

- **[accessibility-component-optimization-summary.md](./accessibility-component-optimization-summary.md)** - 组件优化总结
  - AssetList、AssetForm、AssetBasicInfoSection

- **[ui-ux-implementation-summary.md](./ui-ux-implementation-summary.md)** - 第一阶段总结
  - 设计系统标准化

- **[ui-ux-review-report.md](./ui-ux-review-report.md)** - UI/UX 改进复核报告
- **[ui-ux-improvements-report.md](./ui-ux-improvements-report.md)** - UI/UX 改进报告

### 状态组件
- **[state-components-implementation-summary.md](./state-components-implementation-summary.md)** - 状态组件实施总结
  - Loading、ErrorState、EmptyState 组件
  - 17个子组件，~900行代码

### 移动端优化
- **[mobile-optimization-summary.md](./mobile-optimization-summary.md)** - 移动端体验优化总结
  - 响应式表格组件
  - 触摸目标优化
  - 响应式字体系统

### 深色模式
- **[dark-mode-implementation-summary.md](./dark-mode-implementation-summary.md)** - 深色模式实施总结
  - 主题系统架构
  - 浅色/深色主题配置
  - 主题切换组件
  - 完整的CSS变量系统

### 性能优化
- **[performance-optimization-implementation-summary.md](./performance-optimization-implementation-summary.md)** - 性能优化实施总结
  - 图片懒加载组件
  - 虚拟滚动组件
  - 性能监控工具
  - Web Vitals监控

### 问题修复
- **[emergency-fix-table-layout.md](./emergency-fix-table-layout.md)** - 响应式表格布局修复
- **[breadcrumb-spacing-fix.md](./breadcrumb-spacing-fix.md)** - 面包屑间距修复

## 🛠️ 技术文档

### 性能优化
- **[performance-optimization.md](./performance-optimization.md)** - 性能优化指南

### 类型安全
- **[type-safety-fix-summary.md](./type-safety-fix-summary.md)** - 类型安全修复总结

### 诊断
- **[diagnostic-implementation-summary.md](./diagnostic-implementation-summary.md)** - 诊断工具实施
- **[frontend-diagnostics.md](./frontend-diagnostics.md)** - 前端诊断指南

### 日志
- **[logger-usage.md](./logger-usage.md)** - 日志系统使用指南

## 🎨 UI 指南

- **[UI-STYLE-GUIDE.md](./UI-STYLE-GUIDE.md)** - UI 风格指南
- **[ANIMATION-GUIDE.md](./ANIMATION-GUIDE.md)** - 动画指南

## 📖 使用建议

### 新成员入门
1. 阅读 [design-system.md](./design-system.md) 了解设计规范
2. 阅读 [accessibility-guide.md](./accessibility-guide.md) 了解可访问性要求
3. 参考 [UI-STYLE-GUIDE.md](./UI-STYLE-GUIDE.md) 编写代码

### 组件开发
1. 设计阶段: 参考 [design-system.md](./design-system.md)
2. 可访问性: 参考 [accessibility-guide.md](./accessibility-guide.md)
3. 性能优化: 参考 [performance-optimization.md](./performance-optimization.md)

### 问题排查
1. 类型错误: 参考 [type-safety-fix-summary.md](./type-safety-fix-summary.md)
2. UI 问题: 参考 [ui-ux-review-report.md](./ui-ux-review-report.md)
3. 性能问题: 参考 [performance-optimization.md](./performance-optimization.md)

## 🔧 工具和资源

### 可访问性工具
```typescript
import { generateAriaLabel, announceToScreenReader } from '@/utils/accessibility';
```

### 设计 Token
```css
color: var(--color-primary);
padding: var(--spacing-lg);
```

## 📝 文档维护

- 所有文档使用 Markdown 格式
- 代码示例使用 TypeScript
- 更新文档时请更新本索引

---

**最后更新**: 2026-02-06
**维护者**: 前端开发团队
