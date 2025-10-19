-- 添加密码历史记录和密码最后修改时间字段
ALTER TABLE users ADD COLUMN password_history TEXT;
ALTER TABLE users ADD COLUMN password_last_changed DATETIME;