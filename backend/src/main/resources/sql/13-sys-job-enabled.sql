-- ============================================================
-- 步骤 13：sys_job 启用字段与 bean_name（已有库增量）
-- ============================================================

ALTER TABLE sys_job ADD COLUMN IF NOT EXISTS bean_name VARCHAR(64);
ALTER TABLE sys_job ADD COLUMN IF NOT EXISTS description VARCHAR(512);
ALTER TABLE sys_job ADD COLUMN IF NOT EXISTS enabled CHAR(1) DEFAULT '0';

-- 从 invoke_target 回填 bean_name（若为空）
UPDATE sys_job
SET bean_name = invoke_target
WHERE bean_name IS NULL AND invoke_target IS NOT NULL;

UPDATE sys_job
SET bean_name = 'unknown'
WHERE bean_name IS NULL;

ALTER TABLE sys_job ALTER COLUMN bean_name SET NOT NULL;

-- 旧 status 字段迁移为 enabled（0-正常→1-启用，1-暂停→0-停用）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sys_job' AND column_name = 'status'
    ) THEN
        UPDATE sys_job SET enabled = CASE WHEN status = '0' THEN '1' ELSE '0' END
        WHERE enabled IS NULL OR enabled = '0';
        ALTER TABLE sys_job DROP COLUMN status;
    END IF;
END $$;

UPDATE sys_job SET enabled = '0' WHERE enabled IS NULL;
UPDATE sys_job SET cron_expression = '' WHERE cron_expression IS NULL OR cron_expression = '';

CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_job_bean_name ON sys_job (bean_name);
CREATE INDEX IF NOT EXISTS idx_sys_job_enabled ON sys_job (enabled);
