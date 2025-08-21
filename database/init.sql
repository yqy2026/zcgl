-- 土地房产资产管理系统数据库初始化脚本

-- 创建数据库
CREATE DATABASE IF NOT EXISTS asset_management;

-- 使用数据库
\c asset_management;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建索引优化查询性能
-- 资产表索引
CREATE INDEX IF NOT EXISTS idx_assets_ownership_entity ON assets(ownership_entity);
CREATE INDEX IF NOT EXISTS idx_assets_property_nature ON assets(property_nature);
CREATE INDEX IF NOT EXISTS idx_assets_usage_status ON assets(usage_status);
CREATE INDEX IF NOT EXISTS idx_assets_ownership_status ON assets(ownership_status);
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at);
CREATE INDEX IF NOT EXISTS idx_assets_updated_at ON assets(updated_at);

-- 复合索引用于常见查询组合
CREATE INDEX IF NOT EXISTS idx_assets_nature_status ON assets(property_nature, usage_status);
CREATE INDEX IF NOT EXISTS idx_assets_entity_nature ON assets(ownership_entity, property_nature);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_assets_property_name_gin ON assets USING gin(property_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_assets_address_gin ON assets USING gin(address gin_trgm_ops);

-- 资产历史表索引
CREATE INDEX IF NOT EXISTS idx_asset_history_asset_id ON asset_history(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_history_changed_at ON asset_history(changed_at);
CREATE INDEX IF NOT EXISTS idx_asset_history_change_type ON asset_history(change_type);

-- 资产文档表索引
CREATE INDEX IF NOT EXISTS idx_asset_documents_asset_id ON asset_documents(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_documents_uploaded_at ON asset_documents(uploaded_at);

-- 创建视图用于常见查询
CREATE OR REPLACE VIEW v_asset_summary AS
SELECT 
    id,
    property_name,
    ownership_entity,
    management_entity,
    address,
    actual_property_area,
    rentable_area,
    rented_area,
    unrented_area,
    property_nature,
    usage_status,
    ownership_status,
    CASE 
        WHEN rentable_area > 0 THEN ROUND((rented_area / rentable_area * 100)::numeric, 2)
        ELSE 0
    END as occupancy_rate_calculated,
    created_at,
    updated_at
FROM assets;

-- 创建统计视图
CREATE OR REPLACE VIEW v_asset_statistics AS
SELECT 
    COUNT(*) as total_assets,
    SUM(actual_property_area) as total_area,
    SUM(rentable_area) as total_rentable_area,
    SUM(rented_area) as total_rented_area,
    SUM(unrented_area) as total_unrented_area,
    CASE 
        WHEN SUM(rentable_area) > 0 THEN ROUND((SUM(rented_area) / SUM(rentable_area) * 100)::numeric, 2)
        ELSE 0
    END as overall_occupancy_rate
FROM assets
WHERE property_nature = '经营类';

-- 创建权属方统计视图
CREATE OR REPLACE VIEW v_ownership_statistics AS
SELECT 
    ownership_entity,
    COUNT(*) as asset_count,
    SUM(actual_property_area) as total_area,
    SUM(CASE WHEN property_nature = '经营类' THEN rentable_area ELSE 0 END) as total_rentable_area,
    SUM(CASE WHEN property_nature = '经营类' THEN rented_area ELSE 0 END) as total_rented_area,
    CASE 
        WHEN SUM(CASE WHEN property_nature = '经营类' THEN rentable_area ELSE 0 END) > 0 
        THEN ROUND((SUM(CASE WHEN property_nature = '经营类' THEN rented_area ELSE 0 END) / 
                   SUM(CASE WHEN property_nature = '经营类' THEN rentable_area ELSE 0 END) * 100)::numeric, 2)
        ELSE 0
    END as occupancy_rate
FROM assets
GROUP BY ownership_entity
ORDER BY asset_count DESC;

-- 创建使用状态统计视图
CREATE OR REPLACE VIEW v_usage_statistics AS
SELECT 
    usage_status,
    COUNT(*) as asset_count,
    SUM(actual_property_area) as total_area,
    ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM assets))::numeric, 2) as percentage
FROM assets
GROUP BY usage_status
ORDER BY asset_count DESC;

-- 创建物业性质统计视图
CREATE OR REPLACE VIEW v_property_nature_statistics AS
SELECT 
    property_nature,
    COUNT(*) as asset_count,
    SUM(actual_property_area) as total_area,
    ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM assets))::numeric, 2) as percentage
FROM assets
GROUP BY property_nature;

-- 创建确权状态统计视图
CREATE OR REPLACE VIEW v_ownership_status_statistics AS
SELECT 
    ownership_status,
    COUNT(*) as asset_count,
    SUM(actual_property_area) as total_area,
    ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM assets))::numeric, 2) as percentage
FROM assets
GROUP BY ownership_status
ORDER BY asset_count DESC;

-- 创建存储过程用于数据清理
CREATE OR REPLACE FUNCTION cleanup_old_history()
RETURNS void AS $$
BEGIN
    -- 删除6个月前的历史记录（保留重要变更）
    DELETE FROM asset_history 
    WHERE changed_at < NOW() - INTERVAL '6 months'
    AND change_type != 'delete';
    
    -- 记录清理日志
    INSERT INTO asset_history (asset_id, change_type, changed_fields, new_values, changed_by, reason)
    VALUES (
        '00000000-0000-0000-0000-000000000000',
        'system',
        ARRAY['cleanup'],
        '{"action": "cleanup_old_history", "timestamp": "' || NOW() || '"}',
        'system',
        'Automated cleanup of old history records'
    );
END;
$$ LANGUAGE plpgsql;

-- 创建触发器函数用于自动更新时间戳
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为资产表创建更新时间戳触发器
DROP TRIGGER IF EXISTS update_assets_updated_at ON assets;
CREATE TRIGGER update_assets_updated_at
    BEFORE UPDATE ON assets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 创建触发器函数用于记录变更历史
CREATE OR REPLACE FUNCTION record_asset_changes()
RETURNS TRIGGER AS $$
DECLARE
    changed_fields text[];
    old_values jsonb;
    new_values jsonb;
BEGIN
    -- 检测变更的字段
    changed_fields := ARRAY[]::text[];
    old_values := '{}'::jsonb;
    new_values := '{}'::jsonb;
    
    IF TG_OP = 'UPDATE' THEN
        -- 比较各个字段
        IF OLD.property_name != NEW.property_name THEN
            changed_fields := array_append(changed_fields, 'property_name');
            old_values := old_values || jsonb_build_object('property_name', OLD.property_name);
            new_values := new_values || jsonb_build_object('property_name', NEW.property_name);
        END IF;
        
        IF OLD.ownership_entity != NEW.ownership_entity THEN
            changed_fields := array_append(changed_fields, 'ownership_entity');
            old_values := old_values || jsonb_build_object('ownership_entity', OLD.ownership_entity);
            new_values := new_values || jsonb_build_object('ownership_entity', NEW.ownership_entity);
        END IF;
        
        -- 添加更多字段比较...
        
        -- 只有当有字段变更时才记录
        IF array_length(changed_fields, 1) > 0 THEN
            INSERT INTO asset_history (
                asset_id, change_type, changed_fields, old_values, new_values, changed_by
            ) VALUES (
                NEW.id, 'update', changed_fields, old_values, new_values, 'system'
            );
        END IF;
        
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO asset_history (
            asset_id, change_type, changed_fields, new_values, changed_by
        ) VALUES (
            NEW.id, 'create', ARRAY['all'], to_jsonb(NEW), 'system'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO asset_history (
            asset_id, change_type, changed_fields, old_values, changed_by
        ) VALUES (
            OLD.id, 'delete', ARRAY['all'], to_jsonb(OLD), 'system'
        );
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 为资产表创建变更历史触发器
DROP TRIGGER IF EXISTS record_asset_changes_trigger ON assets;
CREATE TRIGGER record_asset_changes_trigger
    AFTER INSERT OR UPDATE OR DELETE ON assets
    FOR EACH ROW
    EXECUTE FUNCTION record_asset_changes();

-- 创建定期清理任务（需要pg_cron扩展）
-- SELECT cron.schedule('cleanup-old-history', '0 2 * * 0', 'SELECT cleanup_old_history();');

-- 创建性能监控表
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_unit VARCHAR(20),
    metadata JSONB,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- 性能监控表索引
CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_recorded_at ON performance_metrics(recorded_at);

-- 插入初始配置数据
INSERT INTO performance_metrics (metric_name, metric_value, metric_unit, metadata) VALUES
('database_version', 1.0, 'version', '{"description": "Initial database setup"}'),
('last_optimization', EXTRACT(EPOCH FROM NOW()), 'timestamp', '{"description": "Database optimization timestamp"}')
ON CONFLICT DO NOTHING;

-- 创建数据库统计函数
CREATE OR REPLACE FUNCTION get_database_stats()
RETURNS TABLE(
    table_name text,
    row_count bigint,
    table_size text,
    index_size text,
    total_size text
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname||'.'||tablename as table_name,
        n_tup_ins - n_tup_del as row_count,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as table_size,
        pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) + pg_indexes_size(schemaname||'.'||tablename)) as total_size
    FROM pg_stat_user_tables
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- 创建慢查询监控视图
CREATE OR REPLACE VIEW v_slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
WHERE mean_time > 100  -- 平均执行时间超过100ms的查询
ORDER BY mean_time DESC
LIMIT 20;

-- 设置数据库参数优化
-- 这些参数需要在postgresql.conf中设置，这里仅作为参考
/*
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
*/

-- 创建备份恢复函数
CREATE OR REPLACE FUNCTION create_backup_info()
RETURNS void AS $$
BEGIN
    INSERT INTO performance_metrics (metric_name, metric_value, metric_unit, metadata)
    VALUES (
        'backup_created',
        EXTRACT(EPOCH FROM NOW()),
        'timestamp',
        jsonb_build_object(
            'database_size', pg_database_size(current_database()),
            'table_count', (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'),
            'asset_count', (SELECT COUNT(*) FROM assets)
        )
    );
END;
$$ LANGUAGE plpgsql;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成！';
    RAISE NOTICE '已创建索引、视图、触发器和存储过程';
    RAISE NOTICE '数据库已优化用于资产管理系统';
END $$;