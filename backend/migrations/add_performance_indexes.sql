-- 添加性能优化索引
-- 为经常查询的字段添加索引以提高查询性能

-- 资产表索引
CREATE INDEX IF NOT EXISTS "idx_assets_data_status" ON "assets" ("data_status");
CREATE INDEX IF NOT EXISTS "idx_assets_ownership_status" ON "assets" ("ownership_status");
CREATE INDEX IF NOT EXISTS "idx_assets_property_nature" ON "assets" ("property_nature");
CREATE INDEX IF NOT EXISTS "idx_assets_usage_status" ON "assets" ("usage_status");
CREATE INDEX IF NOT EXISTS "idx_assets_business_category" ON "assets" ("business_category");
CREATE INDEX IF NOT EXISTS "idx_assets_ownership_entity" ON "assets" ("ownership_entity");
CREATE INDEX IF NOT EXISTS "idx_assets_project_name" ON "assets" ("project_name");

-- 复合索引用于常见查询组合
CREATE INDEX IF NOT EXISTS "idx_assets_status_nature" ON "assets" ("data_status", "property_nature");
CREATE INDEX IF NOT EXISTS "idx_assets_status_category" ON "assets" ("data_status", "business_category");
CREATE INDEX IF NOT EXISTS "idx_assets_status_ownership" ON "assets" ("data_status", "ownership_status");

-- 文本搜索索引
CREATE INDEX IF NOT EXISTS "idx_assets_property_name" ON "assets" ("property_name");
CREATE INDEX IF NOT EXISTS "idx_assets_address" ON "assets" ("address");

-- 租赁相关索引
CREATE INDEX IF NOT EXISTS "idx_rent_contracts_contract_status" ON "rent_contracts" ("contract_status");
CREATE INDEX IF NOT EXISTS "idx_rent_contracts_tenant_name" ON "rent_contracts" ("tenant_name");
CREATE INDEX IF NOT EXISTS "idx_rent_contracts_asset_id" ON "rent_contracts" ("asset_id");

-- 权属方索引
CREATE INDEX IF NOT EXISTS "idx_ownership_name" ON "ownership" ("name");

-- 项目索引
CREATE INDEX IF NOT EXISTS "idx_project_status" ON "project" ("status");

-- 历史记录索引用于性能监控
CREATE INDEX IF NOT EXISTS "idx_asset_history_operation_time" ON "asset_history" ("operation_time");
CREATE INDEX IF NOT EXISTS "idx_asset_history_asset_id" ON "asset_history" ("asset_id");
CREATE INDEX IF NOT EXISTS "idx_asset_history_field_name" ON "asset_history" ("field_name");

-- 复合历史记录索引
CREATE INDEX IF NOT EXISTS "idx_asset_history_asset_field_time" ON "asset_history" ("asset_id", "field_name", "operation_time");

-- 组织结构索引
CREATE INDEX IF NOT EXISTS "idx_organization_parent_id" ON "organization" ("parent_id");
CREATE INDEX IF NOT EXISTS "idx_organization_name" ON "organization" ("name");

-- 系统字典索引
CREATE INDEX IF NOT EXISTS "idx_system_dict_type" ON "system_dictionaries" ("type");

-- 为统计查询添加的索引
CREATE INDEX IF NOT EXISTS "idx_assets_financial" ON "assets" ("data_status", "annual_income" IS NOT NULL);
CREATE INDEX IF NOT EXISTS "idx_assets_area" ON "assets" ("data_status", "rentable_area" IS NOT NULL);

-- 分析用复合索引
CREATE INDEX IF NOT EXISTS "idx_assets_occupancy_calc" ON "assets" ("data_status", "rentable_area", "rented_area", "include_in_occupancy_rate");

-- 为PDF导入添加的索引
CREATE INDEX IF NOT EXISTS "idx_assets_contract_search" ON "assets" ("lease_contract_number") WHERE "lease_contract_number" IS NOT NULL;