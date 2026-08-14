---
name: 土地物业资产运营管理系统
description: 资产、合同与协议、经营台账、客户与经营分析一体化的内部运营平台
colors:
  primary: "#0e63e5"
  primary-hover: "#1169f0"
  primary-active: "#0958d9"
  primary-light: "#e6f4ff"
  secondary: "#0ea5e9"
  secondary-hover: "#38bdf8"
  secondary-active: "#0284c7"
  success: "#52c41a"
  success-light: "#f6ffed"
  warning: "#faad14"
  warning-light: "#fffbe6"
  error: "#ff4d4f"
  error-light: "#fff2f0"
  info: "#1890ff"
  info-light: "#e6f7ff"
  text-primary: "#262626"
  text-secondary: "#595959"
  text-tertiary: "#717171"
  text-quaternary: "#bfbfbf"
  text-inverse: "#ffffff"
  bg-primary: "#ffffff"
  bg-secondary: "#fafafa"
  bg-tertiary: "#f5f5f5"
  bg-quaternary: "#f0f0f0"
  bg-layout: "#f8fafc"
  bg-hover: "#f1f5f9"
  border: "#d9d9d9"
  border-light: "#f0f0f0"
  border-dark: "#bfbfbf"
  chart-blue: "#1677ff"
  chart-cyan: "#13c2c2"
  chart-green: "#52c41a"
  chart-gold: "#faad14"
  chart-red: "#f5222d"
  chart-magenta: "#eb2f96"
  chart-geekblue: "#2f54eb"
  chart-purple: "#722ed1"
  tag-blue-text: "#0958d9"
  tag-green-text: "#237804"
  tag-gold-text: "#874d00"
  tag-red-text: "#cf1322"
  tag-cyan-text: "#006d75"
  tag-orange-text: "#ad4e00"
  tag-lime-text: "#4f6900"
  tag-volcano-text: "#a8071a"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', 'Microsoft YaHei', sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', 'Microsoft YaHei', sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.5
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', 'Microsoft YaHei', sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', 'Microsoft YaHei', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', 'Microsoft YaHei', sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.5
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  button: "6px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
  xxxl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text-inverse}"
    rounded: "{rounded.button}"
    padding: "8px 20px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
  button-default:
    backgroundColor: "{colors.bg-primary}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.button}"
    padding: "8px 20px"
    height: "36px"
  input:
    backgroundColor: "{colors.bg-primary}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.button}"
    height: "32px"
  card:
    backgroundColor: "{colors.bg-primary}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  table-header:
    backgroundColor: "{colors.bg-layout}"
    textColor: "{colors.text-secondary}"
  nav-item-selected:
    backgroundColor: "rgba(14, 99, 229, 0.08)"
    textColor: "{colors.primary}"
---

# Design System: 土地物业资产运营管理系统

## Overview

**Creative North Star: "台账之屋 The Ledger House"**

这是一座为资产运营专员建造的台账之屋：每个数字都能溯源到一份凭证、一条流水、一个账期；每份合同与协议都以盖章扫描件为事实底座。视觉系统为 Operate 模式服务——用户每天在此完成资产维护、合同补录、台账确认与收缴跟进，**扫描性与信息密度高于装饰**。整体气质冷静、专业、有秩序感：大面积灰蓝布局底、白色纸面容器、克制的蓝色点缀，像银行后台而非展览馆。

组件哲学是「精确而克制」：紧凑的控制高度（32–40px）、细边框、轻阴影、统一的 8px 圆角语言，一切以「一眼看清、快速操作」为目标。颜色极少承担装饰职责——主色资产蓝只出现在可交互与选中态；成功、警告、错误三档语义色承载全部状态表达。

**单一真相源**：颜色/间距/圆角 token 唯一来源是 `frontend/src/styles/variables.css`（CSS 变量层），AntD 组件 token 由 `themeConfig.ts` 对齐到同一组值；二者一致，不存在第三套覆盖层。主色为满足 WCAG AA（白字 ≥4.5:1）由 AntD 默认 `#1677ff` 加深至 `#0e63e5`。**暗色模式已下线**（2026-08-13 收口）：内网桌面工具无暗色驱动需求，原四机制三调色板的半成品暗色（系统媒体查询、`[data-theme]` 覆盖、死掉的 JS 内联注入层、AntD 静态 algorithm）全部移除，只保留 `prefers-contrast: high` 与 `prefers-reduced-motion` 适配。

**Key Characteristics:**
- 页面底为灰蓝色（`#f8fafc`），内容全部浮在白色纸面容器上，层次靠底色与细边框而非阴影
- 主色资产蓝（`#0e63e5`）只用于交互与选中态，从不用于展示性填充
- 全中文界面；业务对象以「合同与协议」「经营台账」等中文名出现，不引入英文页面对象名
- 表格是高频主视图：统一表头底色、悬停行色与 6px 圆角控制件
- 桌面优先（Chrome/Edge），触屏与窄屏以 44px 触控目标与表格转卡片兜底

## Colors

调性是一组冷静的「蓝色 + 中性灰」：暖度趋零、明度分层清晰，任何颜色在页面上都不喧宾夺主。

### Primary
- **资产蓝 Asset Blue** (#0e63e5)：所有主交互——主按钮、链接、选中菜单项、焦点环、行聚焦底色。**为满足 WCAG AA（白字 ≥4.5:1）由 AntD 默认 #1677ff 加深**；悬停 #1169f0、按下 #0958d9（悬停档亦达 AA）。
- **资产蓝浅底** (#e6f4ff)：选中/聚焦的软底色与文本选区，配资产蓝文字。

### Secondary
- **天光蓝 Sky Blue** (#0ea5e9)：次要强调——图表第二序列、信息类点缀。悬停 #38bdf8、按下 #0284c7。

### Tertiary
- 无独立第三强调色；图表与状态全部由语义色与图表序列色承担。

### Chart Colors（冷色系谱）
图表序列色独立于主色，相邻色相距离 ≥30°（由 `contrastFloors` 测试守护），顺序：蓝 `#1677ff` → 青 `#13c2c2` → 绿 `#52c41a` → 金 `#faad14` → 红 `#f5222d` → 靛 `#2f54eb` → 品红 `#eb2f96` → 紫 `#722ed1`。冷色在前（蓝/青/绿），暖色（金/红/品红）只用于深序列，守住冷静调性。

### Tag Text Colors（状态标签文字深档）
AntD 预置/状态 Tag 默认拿 -6/-7 基色当文字，浅底上不足 AA；本项目用 `*-text` token 覆盖到达标深档（global.css 高特异性 `.ant-tag.ant-tag-*:not(.ant-tag-disabled)`）：蓝 #0958d9、绿 #237804、金 #874d00、红 #cf1322、青 #006d75、橙 #ad4e00、青柠 #4f6900、火山 #a8071a。

### Neutral
- **墨色 Ink** (#262626)：主文本，正文与表格内容、标题（`colorTextHeading` 已合流到此值）。
- **铅灰 Lead** (#595959)：次级文本，描述与说明、表头文字、菜单项（themeConfig 已合流）。
- **灰岩 Rock** (#717171)：三级文本，占位与弱化信息（**为达 AA 由 #8c8c8c 加深**）。
- **淡灰 Ash** (#bfbfbf)：四级文本，禁用占位符。
- **纸白** (#ffffff)：容器底。
- **微灰** (#fafafa)：次级容器底（悬停工具栏、禁用输入底）。
- **浅灰** (#f5f5f5)：三级容器底。
- **雾灰** (#f0f0f0)：四级容器底与细分隔线。
- **布局灰蓝** (#f8fafc)：页面布局底（body、表头）。
- **悬停淡蓝灰** (#f1f5f9)：表格行悬停、卡片悬停底。
- **边框**：常规 #d9d9d9、浅 #f0f0f0（表格内部分隔）、深 #bfbfbf（强调边框）。

**暗色模式**：已下线（2026-08-13）。内网桌面工具无暗色驱动需求；原四机制三调色板的半成品暗色（CSS 媒体查询、`[data-theme]` 覆盖、零消费的 JS 内联注入层、AntD 静态 algorithm）全部移除。仅保留 `prefers-contrast: high` 与 `prefers-reduced-motion` 适配。

### Named Rules
**The 克制主色 Rule.** 资产蓝只出现在可交互元素与选中态上。任何展示性数据——统计数字、图表、摘要——不得使用主色填充；它们属于灰阶或语义色。

## Typography

**Display Font:** Inter（回退：-apple-system, Segoe UI, Roboto, Noto Sans, Microsoft YaHei）
**Body Font:** Inter（同上）
**Label/Mono Font:** 无独立等宽；代码与键位使用 source-code-pro / Menlo / Monaco 系统栈

**Character:** 冷静中性的无衬线工具字型。拉丁字符走 Inter，中文自动落入系统字体栈（Noto Sans CJK / 微软雅黑 / PingFang），整体字面紧凑、明度均匀，适合长时间数据浏览。基数为 14px，尺度比约 1.125–1.2，层级靠字号 + 字重（600）而非颜色区分。

### Hierarchy
- **Display**（600, 1.5rem/24px, 1.25）：大数字——统计卡片数值（Statistic content）、关键经营指标。
- **Headline**（600, 1.25rem/20px, 1.5）：页面主标题、分析页大标题。
- **Title**（600, 1rem/16px, 1.5）：卡片标题（`.ant-card-head-title` 统一 semibold 16px）、区块小标题。
- **Body**（400, 0.875rem/14px, 1.5）：正文、表格内容、表单输入（AntD fontSize 14）。表格内长文本不设行宽上限——数据表需要完整可视。
- **Label**（500, 0.8125rem/13px, 1.5）：表单标签、表头、列表项元信息；弱化场景降至 0.75rem/12px。

### Named Rules
**The 层级靠字号 Rule.** 标题与正文之间优先用字号 + 字重区分，不靠颜色深浅制造层级——颜色留给状态语义。

**The 数字对齐 Rule.** 台账类界面数字密集，body、`.ant-table`、`.ant-statistic-content` 全局启用 `font-variant-numeric: tabular-nums`（Inter 支持），金额与编码列等宽对齐、不跳动。

## Layout

- **页面骨架**：Sider + Header + Content。Sider 与 Header 为半透明白（rgba(255,255,255,0.95)），Content 落在布局灰蓝（`#f8fafc`）上；正文容器为白色卡片。
- **页面内边距**：默认 `1.5rem`（pageContainer），紧凑 `1rem`，宽松 `2rem`；响应式容器用 `clamp()` 随视口流动（如 `clamp(0.75rem, 2vw, 1.5rem)`）。
- **间距节奏**：4/8/12/16/24/32/48px 七档。卡片内边距 16px、表单项间距 12px、区块间距 24px 为高频值。
- **断点**：xs 576 / sm 768 / md 992 / lg 1200 / xl 1400 / xxl 1600px。桌面默认按 992px 以上设计，sm 以下进入移动布局。
- **移动端**：表格转卡片视图（ResponsiveTable）、分页居中换行、模态框占满视口（max-width 100vw - 16px、内容区可滚动）、触控目标 44px 起步。
- **模态框宽度档位**：32.5 / 45 / 57.5rem，不做档位外的新尺寸。

## Elevation & Depth

平实为主、状态响应。**静态表面默认平实**——卡片、表格、表单在 rest 态只靠底色与 1px 细边框分层；阴影只在状态变化时出现：悬停升阶、下拉/弹层/模态等浮起面、焦点环。

### Shadow Vocabulary
- **sm**（`0 2px 4px rgba(0,0,0,0.08)`）：卡片默认微影（AntD Card 实际为三层超轻叠加）、按钮基础影。
- **md**（`0 4px 12px rgba(0,0,0,0.1)`）：卡片悬停升阶、下拉面板。
- **lg**（`0 8px 24px rgba(0,0,0,0.12)`）：浮层容器、日期面板。
- **xl**（`0 20px 60px rgba(0,0,0,0.15)`）：模态框、大浮层。

### Named Rules
**The Flat-By-Default Rule.** 表面在 rest 态平实。阴影只作为状态响应出现（悬停、浮起、聚焦），静止内容绝不堆影。

## Shapes

圆角语言统一且克制：基础圆角 8px（卡片、模态框），控制件 6px（按钮、输入框、选择器——比容器略锐，强化工具感），4px 用于小元素（滚动条、标签角），胶囊形（999px）只用于 Tag/Badge 类。边框默认 1px 细线；焦点环为 2px 资产蓝 + 2px 偏移 + 外圈淡蓝光晕（`0 0 0 4px rgba(14,99,229,0.1)`）。

## Components

### Buttons
- **Shape:** 6px 圆角，高 32/36/40px（sm/md/lg），字重 500，14px。
- **Primary:** 资产蓝底（#0e63e5）+ 白字（对比度 5.34:1 达 AA），8px×20px 内边距（md），基础微影；悬停 #1169f0（4.88:1 亦达 AA）、按下 #0958d9。
- **Hover / Focus:** 150ms 标准缓动过渡背景与阴影；`:focus-visible` 显示 2px 资产蓝焦点环 + 偏移。
- **Default:** 纸白底 + 1px 常规边框 + 墨色文字；悬停资产蓝边框与文字。Danger 变体用错误红 `#ff4d4f`。

### Chips / Tags
- **Style:** 胶囊形（999px），浅色底 + 语义色文字。**文字色用 `*-text` 深档 token**（global.css 覆盖 AntD 默认 -6/-7 基色以满足 AA）：成功 #237804、警告 #874d00、错误 #cf1322、信息 #0958d9；中性标签用微灰底 + 次级灰文字。背景浅底保持 AntD 默认（#f6ffed/#fffbe6/#fff2f0/#e6f7ff）。
- **State:** 状态 Tag 无交互态；可筛选的 Tag 选中时切资产蓝浅底 + 资产蓝文字。

### Cards / Containers
- **Corner Style:** 8px。
- **Background:** 纸白；标题区与正文同底，靠 semibold 16px 标题 + 1px 浅边框分层，不用色块卡头。
- **Shadow Strategy:** rest 态超轻微影（AntD 三层叠加），悬停升 md。
- **Border:** 默认无独立边框（靠底色与阴影），需要强分隔时用 `#f0f0f0`。
- **Internal Padding:** 16px（sm 12px / lg 24px 档位）。

### Inputs / Fields
- **Style:** 1px 常规边框 + 纸白底 + 6px 圆角，高 32px，14px 文字。
- **Focus:** 边框切资产蓝 + 2px 淡蓝光晕（非粗边框切换）；错误态红边框 + 红色错误文案，禁用态微灰底 + 淡灰文字。
- **Density:** 表单项垂直间距 12px，标签与控件 4px。

### Table
- **Style:** 表头底 `#f8fafc` + 铅灰文字（#595959）+ 透明分割线；单元格 12px 垂直内边距、1px `#f0f0f0` 行分隔；行悬停 `#f1f5f9`。
- **Focus:** 键盘导航行聚焦为资产蓝浅底 + 2px 资产蓝 outline。

### Navigation
- **Style:** Sider/Header 半透明白（0.95），菜单项透明底、石板文字；选中项为 `rgba(22,119,255,0.08)` 浅蓝底 + 资产蓝文字；悬停资产蓝文字。移动端收起为抽屉。

### Statistic
- **Style:** 标题 14px 灰岩色，数值 24px semibold 墨色；趋势箭头用语义色（上升绿/下降红按口径配置，`getTrendColor`）。

### Modal
- **Style:** 8px 圆角，白底 + lg 阴影；头部 16px×24px 内边距（标题 16px semibold）、正文 24px、底部 12px×24px。宽度档位 32.5/45/57.5rem。

## Do's and Don'ts

### Do:
- **Do** 走 token：颜色、间距、圆角一律用 `variables.css` 的 CSS 变量（遗留硬编码经 `colorMap.ts` 收敛），禁止新写裸色值。
- **Do** 守护单一真相源：token 唯一在 `variables.css`（CSS 层）+ `themeConfig.ts`（AntD 层，与 CSS 层同值）；新增主题机制前先问能否复用既有 token。
- **Do** 让主色只出现在交互与选中态——按钮、链接、选中、焦点环、行聚焦；展示数据用灰阶与语义色。
- **Do** 保证文本对比度 ≥4.5:1（WCAG AA）；`contrastFloors` 测试是回归防线，改色后必跑。
- **Do** 保持 rest 态表面平实，阴影只随状态（hover / 浮层 / 焦点）出现。
- **Do** 维持统一密度：控制件 32–40px 高、表格单元 12px 垂直内边距、表单项 12px 间距；台账数字启用 `tabular-nums`。
- **Do** 为所有 `:focus-visible` 元素提供 2px 资产蓝焦点环；尊重 `prefers-reduced-motion` 与 `prefers-contrast: high`（全局样式已实现，新代码不得破坏）。
- **Do** 使用语义色表达状态：成功绿 / 警告琥珀 / 错误红，配对应浅底 Tag（文字用 `*-text` 深档）。
- **Do** 移动与触屏场景保证 44px 触控目标，窄屏表格转卡片视图。

### Don't:
- **Don't** 为展示性数据（统计数字、图表、摘要卡片）添加主色填充或渐变装饰。
- **Don't** 在 rest 态堆叠阴影或使用比 xl 更重的投影。
- **Don't** 绕过既有档位发明新尺寸——新断点、新模态宽度、新间距档位都需要先复用现有 token。
- **Don't** 让界面出现英文业务对象名（用户侧统一「合同与协议」「经营台账」等中文名）。
- **Don't** 用颜色深浅替代字号层级来表达标题/正文差异。
- **Don't** 重新引入暗色模式或多套主题真相源——暗色已下线，复引入需先定义单一真相源与 AntD algorithm 切换，不得再走半成品覆盖层。
- **Don't** 给图表序列用主色/语义色混排——图表走 `CHART_COLORS` 冷色系谱（8 色，相邻色相 ≥30°）。
- **Don't** 为一次性场景新造色板——图表与状态色复用 `CHART_COLORS` / 语义色。
