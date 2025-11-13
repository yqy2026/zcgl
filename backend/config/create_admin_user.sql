
-- 创建管理员用户的SQL脚本
-- 生成时间: 2025-11-09T13:31:40.782230+00:00

-- 注意: 此脚本包含敏感信息，使用后请立即删除

INSERT OR REPLACE INTO users (
    id,
    username,
    email,
    full_name,
    password_hash,
    role,
    is_active,
    is_locked,
    failed_login_attempts,
    created_at,
    updated_at
) VALUES (
    'admin-20251109133140',
    'admin',
    'admin@zcgl.system',
    '系统管理员',
    '3870c66419482c2f702982b3a80c3cb0fc03425ba5e078e31e0fa8c5e64b6175',
    'admin',
    1,
    0,
    0,
    '2025-11-09T13:31:40.782230+00:00',
    '2025-11-09T13:31:40.782230+00:00'
);

-- 管理员登录信息:
-- 用户名: admin
-- 密码: $$jw[:@sCaY6Az).
--
-- 请登录后立即修改密码！
