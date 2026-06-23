# 企业微信 userid 映射与真实发送验证

**状态**：🔄 外部验证 / 映射待补  
**来源**：`docs/archive/issues/2026-06-18-prd-grill-code-followup.md` 的 I2② 拆分残余项  
**范围**：仅跟踪企业微信应用消息的上线前剩余工作，不再承载 2026-06-18 PRD grill 其他已完成代码项。

## 背景

企业微信群机器人广播路径已下线，后端已接入自建应用消息：

- `backend/src/core/config_llm.py` 读取 `WECOM_CORP_ID` / `WECOM_AGENT_ID` / `WECOM_SECRET` / `WECOM_TEST_TOUSER`
- `backend/src/services/notification/wecom_service.py` 通过 `gettoken` + `message/send` 按 `touser` 发送应用消息
- `backend/src/services/notification/scheduler.py` 当前以 `notification.recipient_id` 作为 `touser` 定向发送，并保证企业微信失败不影响站内通知创建

本地已验证企业微信凭据可获取 `access_token`：

```text
errcode=0
errmsg=ok
access_token_set=True
expires_in=7200
```

真实发送测试被企业微信后台可信 IP 限制拦截：

```text
errcode=60020
errmsg=not allow to access from your ip
from ip: 183.6.50.62
```

## 剩余工作

1. **真实发送验证**

   等企业微信后台完成可信 IP / 可信域名 / 接收消息服务器 URL 等前置配置后，复测真实应用消息发送。

2. **正式 userid 映射**

   不能长期依赖 `recipient_id == touser` 的本地假设。上线前需补系统用户到企业微信 `userid` 的映射。

   MVP 推荐方案：

   - 在用户资料上增加 `wecom_userid` 字段，或建立窄表 `user_external_identities`
   - 发送前由系统用户 id 查到企业微信 userid
   - 缺少映射时只创建站内通知，不发送企业微信，并写入清晰 `wecom_send_error`

## 验收

- 未配置可信 IP / 域名时，真实发送失败原因能明确指向企业微信 `errcode=60020`，不影响站内通知。
- 配置可信 IP / 域名后，测试用户能收到企业微信应用消息。
- 系统用户 id 与企业微信 userid 不一致时，发送逻辑读取正式映射，不再依赖 `recipient_id == touser`。
- 缺少映射时不误发给其他人，且错误可诊断。

