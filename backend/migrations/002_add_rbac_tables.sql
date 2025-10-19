-- 创建RBAC相关表
-- Migration: 002_add_rbac_tables
-- Date: 2025-10-14

-- 创建角色权限关联表
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

-- 创建用户角色关联表
CREATE TABLE IF NOT EXISTS user_role_assignments (
    user_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by TEXT,
    expires_at DATETIME,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
);

-- 创建角色表
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    level INTEGER NOT NULL DEFAULT 1,
    category TEXT,
    is_system_role BOOLEAN NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    organization_id TEXT,
    scope TEXT NOT NULL DEFAULT 'global',
    scope_id TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE SET NULL
);

-- 创建权限表
CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    is_system_permission BOOLEAN NOT NULL DEFAULT 0,
    requires_approval BOOLEAN NOT NULL DEFAULT 0,
    max_level INTEGER,
    conditions TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT
);

-- 创建用户角色分配详细表
CREATE TABLE IF NOT EXISTS user_role_assignments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    assigned_by TEXT,
    assigned_at DATETIME NOT NULL,
    expires_at DATETIME,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    reason TEXT,
    notes TEXT,
    context TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
);

-- 创建资源权限表
CREATE TABLE IF NOT EXISTS resource_permissions (
    id TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    user_id TEXT,
    role_id TEXT,
    permission_id TEXT,
    permission_level TEXT NOT NULL DEFAULT 'read',
    granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    granted_by TEXT,
    reason TEXT,
    conditions TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE SET NULL,
    FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE SET NULL
);

-- 创建权限审计日志表
CREATE TABLE IF NOT EXISTS permission_audit_logs (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    user_id TEXT,
    operator_id TEXT,
    old_permissions TEXT,
    new_permissions TEXT,
    reason TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (operator_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS idx_roles_category ON roles(category);
CREATE INDEX IF NOT EXISTS idx_roles_is_active ON roles(is_active);
CREATE INDEX IF NOT EXISTS idx_roles_organization_id ON roles(organization_id);

CREATE INDEX IF NOT EXISTS idx_permissions_name ON permissions(name);
CREATE INDEX IF NOT EXISTS idx_permissions_resource ON permissions(resource);
CREATE INDEX IF NOT EXISTS idx_permissions_action ON permissions(action);
CREATE INDEX IF NOT EXISTS idx_permissions_resource_action ON permissions(resource, action);

CREATE INDEX IF NOT EXISTS idx_user_role_assignments_user_id ON user_role_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_role_id ON user_role_assignments(role_id);
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_is_active ON user_role_assignments(is_active);
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_expires_at ON user_role_assignments(expires_at);

CREATE INDEX IF NOT EXISTS idx_resource_permissions_resource ON resource_permissions(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_resource_permissions_user_id ON resource_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_resource_permissions_is_active ON resource_permissions(is_active);

CREATE INDEX IF NOT EXISTS idx_permission_audit_logs_action ON permission_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_permission_audit_logs_user_id ON permission_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_permission_audit_logs_operator_id ON permission_audit_logs(operator_id);
CREATE INDEX IF NOT EXISTS idx_permission_audit_logs_created_at ON permission_audit_logs(created_at);

-- 插入基础系统角色
INSERT OR IGNORE INTO roles (
    id,
    name,
    display_name,
    description,
    level,
    category,
    is_system_role,
    is_active,
    scope,
    created_at,
    updated_at,
    created_by
) VALUES
-- 系统管理员角色
(
    'role-super-admin',
    'super_admin',
    '超级管理员',
    '拥有系统所有权限的超级管理员角色',
    1,
    'system',
    1,
    1,
    'global',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
-- 资产管理员角色
(
    'role-asset-admin',
    'asset_admin',
    '资产管理员',
    '负责资产管理的管理员角色',
    2,
    'business',
    1,
    1,
    'global',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
-- 资产查看员角色
(
    'role-asset-viewer',
    'asset_viewer',
    '资产查看员',
    '只能查看资产信息的普通用户角色',
    3,
    'business',
    1,
    1,
    'global',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
-- 租赁管理员角色
(
    'role-rent-admin',
    'rent_admin',
    '租赁管理员',
    '负责租赁合同管理的管理员角色',
    2,
    'business',
    1,
    1,
    'global',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
-- 项目管理员角色
(
    'role-project-admin',
    'project_admin',
    '项目管理员',
    '负责项目管理的管理员角色',
    2,
    'business',
    1,
    1,
    'global',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
-- 组织管理员角色
(
    'role-org-admin',
    'org_admin',
    '组织管理员',
    '负责组织架构管理的管理员角色',
    2,
    'business',
    1,
    1,
    'global',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
);

-- 插入基础系统权限
INSERT OR IGNORE INTO permissions (
    id,
    name,
    display_name,
    description,
    resource,
    action,
    is_system_permission,
    requires_approval,
    created_at,
    updated_at,
    created_by
) VALUES
-- 资产权限
(
    'perm-asset-read',
    'asset:read',
    '查看资产',
    '查看资产列表和详情的权限',
    'asset',
    'read',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-asset-create',
    'asset:create',
    '创建资产',
    '创建新资产的权限',
    'asset',
    'create',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-asset-update',
    'asset:update',
    '更新资产',
    '修改资产信息的权限',
    'asset',
    'update',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-asset-delete',
    'asset:delete',
    '删除资产',
    '删除资产的权限',
    'asset',
    'delete',
    1,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),

-- 项目权限
(
    'perm-project-read',
    'project:read',
    '查看项目',
    '查看项目列表和详情的权限',
    'project',
    'read',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-project-create',
    'project:create',
    '创建项目',
    '创建新项目的权限',
    'project',
    'create',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-project-update',
    'project:update',
    '更新项目',
    '修改项目信息的权限',
    'project',
    'update',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-project-delete',
    'project:delete',
    '删除项目',
    '删除项目的权限',
    'project',
    'delete',
    1,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),

-- 租赁合同权限
(
    'perm-rent-read',
    'rent:read',
    '查看租赁合同',
    '查看租赁合同列表和详情的权限',
    'rent_contract',
    'read',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-rent-create',
    'rent:create',
    '创建租赁合同',
    '创建新租赁合同的权限',
    'rent_contract',
    'create',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-rent-update',
    'rent:update',
    '更新租赁合同',
    '修改租赁合同信息的权限',
    'rent_contract',
    'update',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-rent-delete',
    'rent:delete',
    '删除租赁合同',
    '删除租赁合同的权限',
    'rent_contract',
    'delete',
    1,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),

-- 组织权限
(
    'perm-org-read',
    'org:read',
    '查看组织',
    '查看组织架构和员工信息的权限',
    'organization',
    'read',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-org-create',
    'org:create',
    '创建组织',
    '创建新组织的权限',
    'organization',
    'create',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-org-update',
    'org:update',
    '更新组织',
    '修改组织信息的权限',
    'organization',
    'update',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),
(
    'perm-org-delete',
    'org:delete',
    '删除组织',
    '删除组织的权限',
    'organization',
    'delete',
    1,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),

-- 权限管理权限
(
    'perm-rbac-manage',
    'rbac:manage',
    '权限管理',
    '管理角色和权限的权限',
    'rbac',
    'manage',
    1,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),

-- 系统管理权限
(
    'perm-system-manage',
    'system:manage',
    '系统管理',
    '管理系统设置和配置的权限',
    'system',
    'manage',
    1,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
),

-- 统计权限
(
    'perm-stats-read',
    'stats:read',
    '查看统计',
    '查看统计报表和数据分析的权限',
    'statistics',
    'read',
    1,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'system'
);

-- 为超级管理员角色分配所有权限
INSERT OR IGNORE INTO role_permissions (role_id, permission_id, created_by)
SELECT 'role-super-admin', id, 'system' FROM permissions;

-- 为资产管理员角色分配资产相关权限
INSERT OR IGNORE INTO role_permissions (role_id, permission_id, created_by)
SELECT 'role-asset-admin', id, 'system' FROM permissions
WHERE resource = 'asset' OR resource = 'statistics';

-- 为资产查看员角色分配只读权限
INSERT OR IGNORE INTO role_permissions (role_id, permission_id, created_by)
SELECT 'role-asset-viewer', id, 'system' FROM permissions
WHERE action = 'read';

-- 为租赁管理员角色分配租赁相关权限
INSERT OR IGNORE INTO role_permissions (role_id, permission_id, created_by)
SELECT 'role-rent-admin', id, 'system' FROM permissions
WHERE resource = 'rent_contract' OR resource = 'statistics';

-- 为项目管理员角色分配项目相关权限
INSERT OR IGNORE INTO role_permissions (role_id, permission_id, created_by)
SELECT 'role-project-admin', id, 'system' FROM permissions
WHERE resource = 'project' OR resource = 'statistics';

-- 为组织管理员角色分配组织相关权限
INSERT OR IGNORE INTO role_permissions (role_id, permission_id, created_by)
SELECT 'role-org-admin', id, 'system' FROM permissions
WHERE resource = 'organization' OR resource = 'statistics';

-- 插入权限审计日志记录
INSERT OR IGNORE INTO permission_audit_logs (
    id,
    action,
    resource_type,
    resource_id,
    operator_id,
    new_permissions,
    reason,
    created_at
) VALUES
(
    'audit-rbac-init',
    'rbac_init',
    'rbac_system',
    'all',
    'system',
    '{"roles": ["super_admin", "asset_admin", "asset_viewer", "rent_admin", "project_admin", "org_admin"], "permissions": "all_system_permissions"}',
    'RBAC系统初始化',
    CURRENT_TIMESTAMP
);