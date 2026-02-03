# PDF 处理服务

## ✅ Status
**当前状态**: Draft (2026-02-03)

## 接口入口
- Base: `/api/v1/pdf-import`

## 典型流程
1. 上传 PDF 文件
2. 创建或关联处理会话
3. 获取提取结果并确认导入

## 相关代码
- 路由入口: `backend/src/api/v1/documents/pdf_import.py`
- 上传处理: `backend/src/api/v1/documents/pdf_upload.py`
- 前端页面: `frontend/src/pages/Contract/ContractImportUpload.tsx`
