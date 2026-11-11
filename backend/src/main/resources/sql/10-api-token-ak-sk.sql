-- AK/SK API Token 增量脚本
-- 适用于已经执行过旧版 07-scaffold-tables.sql 的数据库。
-- 若重新初始化数据库，请直接使用更新后的 07-scaffold-tables.sql。

ALTER TABLE api_token ADD COLUMN IF NOT EXISTS access_key VARCHAR(64);
ALTER TABLE api_token ADD COLUMN IF NOT EXISTS user_id BIGINT;
ALTER TABLE api_token ADD COLUMN IF NOT EXISTS detail VARCHAR(512);
ALTER TABLE api_token ADD COLUMN IF NOT EXISTS asset TEXT;
ALTER TABLE api_token ADD COLUMN IF NOT EXISTS secret_key VARCHAR(1024);

-- 旧数据无法推导所属用户和授权资源，执行前请先人工迁移或清理旧 api_token 数据。
-- 下面约束和主键变更应在旧数据处理完成后执行：
-- ALTER TABLE api_token ALTER COLUMN access_key SET NOT NULL;
-- ALTER TABLE api_token ADD CONSTRAINT pk_api_token_access_key PRIMARY KEY (access_key);
-- ALTER TABLE api_token ADD CONSTRAINT fk_api_token_user
--     FOREIGN KEY (user_id) REFERENCES sys_user (user_id);

CREATE INDEX IF NOT EXISTS idx_api_token_user ON api_token (user_id);
CREATE INDEX IF NOT EXISTS idx_api_token_status ON api_token (status);
