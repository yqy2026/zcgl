# Capability Guard 环境证据（Day-0 模板）

> 用途：记录 capability guard 在目标环境中的启用证据。

## 环境声明来源（A/B/C）
- 选项：`A | B | C`
- 说明：`<source of truth>`

## startup-log
- 日志片段：`<paste log excerpt>`
- 时间戳：`YYYY-MM-DD HH:mm:ss`

## release-id
- ` <release-id> `

## ci-assert
- 断言项：`<assertion>`
- 结果：`pass | fail`
- 证据链接：`<url or artifact>`

## runtime-flag-value
- 变量：`VITE_ENABLE_CAPABILITY_GUARD`
- 值：`true | false`
- 读取方式：`<how verified>`

## protected-route-check
- 路由：`<route>`
- 预期：`allow | deny`
- 实际：`allow | deny`
- 结论：`pass | fail`
