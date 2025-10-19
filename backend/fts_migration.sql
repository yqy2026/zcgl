-- FTS Migration Script for Production
-- Execute this script to enable FTS on production databases

-- Create FTS virtual tables
CREATE VIRTUAL TABLE IF NOT EXISTS assets_fts USING fts5(
    id UNINDEXED,
    property_name,
    address,
    ownership_entity,
    business_category,
    project_name,
    tenant_name,
    notes,
    certificated_usage,
    actual_usage,
    manager_name,
    tags,
    content='assets',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS projects_fts USING fts5(
    id UNINDEXED,
    name,
    short_name,
    code,
    project_type,
    project_description,
    address,
    city,
    management_entity,
    content='projects',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS ownerships_fts USING fts5(
    id UNINDEXED,
    name,
    code,
    short_name,
    contact_person,
    address,
    business_scope,
    content='ownerships',
    content_rowid='rowid'
);

-- Populate FTS tables (run once)
INSERT INTO assets_fts (id, property_name, address, ownership_entity,
    business_category, project_name, tenant_name, notes,
    certificated_usage, actual_usage, manager_name, tags)
SELECT id, property_name, address, ownership_entity,
       business_category, project_name, tenant_name, notes,
       certificated_usage, actual_usage, manager_name, tags
FROM assets;

INSERT INTO projects_fts (id, name, short_name, code, project_type,
    project_description, address, city, management_entity)
SELECT id, name, short_name, code, project_type,
       project_description, address, city, management_entity
FROM projects;

INSERT INTO ownerships_fts (id, name, code, short_name, contact_person,
    address, business_scope)
SELECT id, name, code, short_name, contact_person,
       address, business_scope
FROM ownerships;

-- Create synchronization triggers
CREATE TRIGGER IF NOT EXISTS assets_fts_insert AFTER INSERT ON assets BEGIN
    INSERT INTO assets_fts (id, property_name, address, ownership_entity,
        business_category, project_name, tenant_name, notes,
        certificated_usage, actual_usage, manager_name, tags)
    VALUES (NEW.id, NEW.property_name, NEW.address, NEW.ownership_entity,
           NEW.business_category, NEW.project_name, NEW.tenant_name, NEW.notes,
           NEW.certificated_usage, NEW.actual_usage, NEW.manager_name, NEW.tags);
END;

CREATE TRIGGER IF NOT EXISTS assets_fts_update AFTER UPDATE ON assets BEGIN
    DELETE FROM assets_fts WHERE id = OLD.id;
    INSERT INTO assets_fts (id, property_name, address, ownership_entity,
        business_category, project_name, tenant_name, notes,
        certificated_usage, actual_usage, manager_name, tags)
    VALUES (NEW.id, NEW.property_name, NEW.address, NEW.ownership_entity,
           NEW.business_category, NEW.project_name, NEW.tenant_name, NEW.notes,
           NEW.certificated_usage, NEW.actual_usage, NEW.manager_name, NEW.tags);
END;

CREATE TRIGGER IF NOT EXISTS assets_fts_delete AFTER DELETE ON assets BEGIN
    DELETE FROM assets_fts WHERE id = OLD.id;
END;

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at);
CREATE INDEX IF NOT EXISTS idx_ownerships_created_at ON ownerships(created_at);
