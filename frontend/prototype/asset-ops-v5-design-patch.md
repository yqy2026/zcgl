# DESIGN.md 修订建议（随 v5 重构一并落地）

问题不在 token，DESIGN.md 的色板、间距、圆角体系全部沿用。只改下面几条：按原文执行会让界面走样，或者与原文自身的规则冲突。

## 1. 状态标签改为小方角

- 现行：Chips / Tags 为胶囊形，圆角 999px。
- 改为：**圆角 4px（`rounded.sm`）**，高 20–22px，12px/600，浅底配 `*-text` 深色字。
- 理由：在密集表格里，胶囊形会在单元格中“浮起来”，和数字列对不齐；4px 方角更像台账。胶囊形只保留给计数徽标（Badge）。

## 2. 卡片静止状态不加阴影

- 现行：Cards 章节写“rest 态超轻微影（AntD 三层叠加）”，但 Elevation 章节又规定“The Flat-By-Default Rule”，两处冲突。
- 改为：卡片、表格、抽屉在静止状态**只用 1px `--border-light` 描边**，`box-shadow: none`。阴影只用于弹窗、下拉面板和浮层。
- AntD 侧：`Card` 设置 `variant="outlined"`，在 `themeConfig.ts` 里把 `boxShadowTertiary` 置为 none，或在组件层覆盖。

## 3. 字体去掉 Inter

- 现行：`fontFamily: Inter, -apple-system, …`。
- 改为：`-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Noto Sans SC", "Segoe UI", sans-serif`。
- 理由：界面是纯中文，Inter 只影响数字和英文字符，却要额外加载字体文件；系统字体在中文环境下与它的视觉差异很小。数字等宽（tabular-nums）在系统字体下同样生效。

## 4. 补充：AntD 默认样式需要压住的地方

这些地方 DESIGN.md 没写，如果开发直接用 AntD 默认值，原型的观感会丢失：

| 组件 | 默认问题 | 约定 |
|---|---|---|
| Table | 行高偏大，表头偏重 | `size="middle"`，行高 42–52px；表头背景 `--bg-secondary`，12px 次级色，字重 400；无竖线 |
| Table 行选中 | 默认无选中态 | 选中行：`--primary-light` 底色 + 左侧 2px 主色 inset 阴影 |
| Card 头 | 带分隔线和色块头 | 标题 15px/600，与正文同底，不使用 `Card` 的 head 区色块 |
| Tabs | 下划线粗、间距大 | 高 56px，选中为 2px 主色下划线，未选中为次级文字色 |
| Segmented（筛选） | 正常 | 用于列表筛选，每项带数量 |
| Drawer | 默认是浮层 | 详情抽屉**常驻在右侧栏**，不弹层、不加遮罩 |
| Button | 页内多个主按钮 | 每页只保留一个 `type="primary"`，其余为 default |

## 5. 删除旧页面副标题规范

旧原型每页 h1 下面都有一行解释性的副标题，新规范中**取消**。规则说明只在相关操作旁边以提示形式出现，例如按钮禁用的原因、越界提示。
