# Phase 3c 产权证接口契约冻结（Day-0）

> 用途：关闭 P3c 进入门禁中的“产权证接口契约冻结”未决项，明确前后端在 Phase 3 的唯一消费口径。

## 元信息
- 日期：`2026-02-27`
- 责任人：`phase3-preflight`
- release-id：`phase3-preflight-20260227`
- 范围：`Phase 3c property_certificate contract`

## 冻结结论
1. 选项：`B（保持 owners[] 兼容契约）`
2. 结论：`property_certificate` 模块在 Phase 3 不引入 `party_relations[]`；导入确认链路与前端类型统一以 `owners[]` 为准。
3. 约束：新增 `party_relations[]` 只能以“向后兼容新增字段”方式进入，且不影响 `owners[]` 在 Phase 3 的可用性。

## 代码证据
1. 后端导入确认请求体显式定义 `owners`：
   - `backend/src/schemas/property_certificate.py:119`
   - `backend/src/schemas/property_certificate.py:127`
2. 后端导入服务显式消费 `owners`：
   - `backend/src/services/property_certificate/service.py:266`
   - `backend/src/services/property_certificate/service.py:333`
3. 后端响应模型 `PropertyCertificateResponse` 显式定义 `owners[]`，且未定义 `party_relations[]`：
   - `backend/src/schemas/property_certificate.py:196`
   - `backend/src/schemas/property_certificate.py:201`
   - `backend/src/schemas/property_certificate.py:214`
4. 产权证列表/详情/创建路由响应均绑定 `PropertyCertificateResponse`：
   - `backend/src/api/v1/assets/property_certificate.py:308`
   - `backend/src/api/v1/assets/property_certificate.py:357`
   - `backend/src/api/v1/assets/property_certificate.py:408`
5. 前端类型与导入测试均使用 `owners`：
   - `frontend/src/types/propertyCertificate.ts:81`
   - `frontend/src/types/propertyCertificate.ts:87`
   - `frontend/src/pages/PropertyCertificate/__tests__/PropertyCertificateImport.test.tsx:58`
   - `frontend/src/pages/PropertyCertificate/__tests__/PropertyCertificateImport.test.tsx:64`
6. 单测校验后端响应契约包含并可序列化 `owners`：
   - `backend/tests/unit/schemas/test_property_certificate_response_schema.py`

## 联调样本（冻结版）

### `POST /api/v1/property-certificates/confirm-import` 请求
```json
{
  "session_id": "session-123",
  "asset_ids": [],
  "extracted_data": {
    "certificate_number": "CERT-001"
  },
  "asset_link_id": null,
  "should_create_new_asset": false,
  "owners": []
}
```

### `POST /api/v1/property-certificates/confirm-import` 响应
```json
{
  "certificate_id": "cert-001",
  "status": "success"
}
```

## 前端消费规则（P3c）
1. 导入确认提交必须携带 `owners[]`（可为空数组）。
2. 页面/服务层不得假设存在 `party_relations[]`。
3. 详情页继续以容错方式读取 `owners`（示例：`certificate.owners ?? []`，`frontend/src/pages/PropertyCertificate/PropertyCertificateDetailPage.tsx:367`）。
