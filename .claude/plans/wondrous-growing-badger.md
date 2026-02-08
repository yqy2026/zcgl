# Plan: Fix All Missing Breadcrumbs (Property Certificate & Others)

## Status
- [x] Phase 1: Comprehensive Route Audit
- [ ] Phase 2: Configuration Update
- [ ] Phase 3: Verification

## Phase 1: Comprehensive Route Audit (Completed)
- Identified missing mappings for Property Certificates, Ownership, Projects, and System sub-modules.
- Identified path inconsistencies (`/financial` vs `/finance`).

## Phase 2: Configuration Update
Goal: Add ALL missing mappings to `frontend/src/config/breadcrumb.ts`.

- [ ] Update `frontend/src/config/breadcrumb.ts` with the following changes:
    - **Property Certificates**:
        - Static: `/property-certificates`: '产权证管理', `/property-certificates/import`: '导入产权证'
        - Dynamic: `/property-certificates/:id`: '产权证详情'
    - **Ownership**:
        - Static: `/ownership`: '权属方管理'
        - Dynamic: `/ownership/:id`: '权属方详情', `/ownership/:id/edit`: '编辑权属方'
    - **Projects**:
        - Static: `/project`: '项目管理'
        - Dynamic: `/project/:id`: '项目详情', `/project/:id/edit`: '编辑项目'
    - **System**:
        - Static: `/system/organizations`: '组织架构', `/system/dictionaries`: '字典管理', `/system/templates`: '模板管理', `/system/settings`: '系统设置'
        - Rename `/system` to '系统管理'
    - **Rental/Assets**:
        - Static: `/rental/contracts/pdf-import`: '导入合同', `/rental/ledger`: '租金台账', `/rental/statistics`: '租赁统计', `/assets/analytics-simple`: '简易分析'
        - Dynamic: `/rental/contracts/:id/edit`: '编辑合同'
    - **Fixes**:
        - Rename `/financial` to `/finance` to match routes.
        - Remove redundant static mappings like `/assets/detail` (covered by dynamic).

## Phase 3: Verification
- [ ] Verify that static routes (e.g. `/import`) take precedence over dynamic ID routes.
