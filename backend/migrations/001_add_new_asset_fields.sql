-- 数据库字段重构迁移脚本
-- 版本：001
-- 描述：添加新的资产管理字段

-- 开始事务
BEGIN TRANSACTION;

-- 添加新字段
ALTER TABLE assets ADD COLUMN land_area REAL;
ALTER TABLE assets ADD COLUMN total_building_area REAL;
ALTER TABLE assets ADD COLUMN actual_property_area REAL;
ALTER TABLE assets ADD COLUMN rentable_area REAL;
ALTER TABLE assets ADD COLUMN rented_area REAL;
ALTER TABLE assets ADD COLUMN unrented_area REAL;
ALTER TABLE assets ADD COLUMN non_commercial_area REAL;
ALTER TABLE assets ADD COLUMN occupancy_rate REAL;
ALTER TABLE assets ADD COLUMN include_in_occupancy_rate INTEGER NOT NULL DEFAULT 1;
ALTER TABLE assets ADD COLUMN certificated_usage VARCHAR(100);
ALTER TABLE assets ADD COLUMN actual_usage VARCHAR(100);
ALTER TABLE assets ADD COLUMN tenant_name VARCHAR(200);
ALTER TABLE assets ADD COLUMN tenant_contact VARCHAR(100);
ALTER TABLE assets ADD COLUMN tenant_type VARCHAR(20);
ALTER TABLE assets ADD COLUMN lease_contract_number VARCHAR(100);
ALTER TABLE assets ADD COLUMN contract_start_date DATE;
ALTER TABLE assets ADD COLUMN contract_end_date DATE;
ALTER TABLE assets ADD COLUMN contract_status VARCHAR(20);
ALTER TABLE assets ADD COLUMN monthly_rent REAL;
ALTER TABLE assets ADD COLUMN deposit REAL;
ALTER TABLE assets ADD COLUMN is_sublease INTEGER NOT NULL DEFAULT 0;
ALTER TABLE assets ADD COLUMN sublease_notes TEXT;
ALTER TABLE assets ADD COLUMN manager_name VARCHAR(100);
ALTER TABLE assets ADD COLUMN business_model VARCHAR(50);
ALTER TABLE assets ADD COLUMN operation_status VARCHAR(20);
ALTER TABLE assets ADD COLUMN annual_income REAL;
ALTER TABLE assets ADD COLUMN annual_expense REAL;
ALTER TABLE assets ADD COLUMN net_income REAL;
ALTER TABLE assets ADD COLUMN operation_agreement_start_date DATE;
ALTER TABLE assets ADD COLUMN operation_agreement_end_date DATE;
ALTER TABLE assets ADD COLUMN operation_agreement_attachments TEXT;
ALTER TABLE assets ADD COLUMN project_name VARCHAR(200);
ALTER TABLE assets ADD COLUMN project_short_name VARCHAR(100);
ALTER TABLE assets ADD COLUMN ownership_category VARCHAR(100);
ALTER TABLE assets ADD COLUMN data_status VARCHAR(20) NOT NULL DEFAULT '正常';
ALTER TABLE assets ADD COLUMN created_by VARCHAR(100);
ALTER TABLE assets ADD COLUMN updated_by VARCHAR(100);
ALTER TABLE assets ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE assets ADD COLUMN tags TEXT;
ALTER TABLE assets ADD COLUMN last_audit_date DATE;
ALTER TABLE assets ADD COLUMN audit_status VARCHAR(20);
ALTER TABLE assets ADD COLUMN auditor VARCHAR(100);
ALTER TABLE assets ADD COLUMN audit_notes TEXT;

-- 数据迁移
UPDATE assets SET 
    actual_property_area = total_area,
    rentable_area = usable_area
WHERE total_area IS NOT NULL OR usable_area IS NOT NULL;

-- 提交事务
COMMIT;