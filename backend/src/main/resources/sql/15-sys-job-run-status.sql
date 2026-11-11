-- ============================================================
-- 步骤 15：sys_job 执行状态字段（已有库增量）
-- ============================================================

-- status 表示最近一次执行状态，与 enabled（启用/停用）分离
ALTER TABLE sys_job ADD COLUMN IF NOT EXISTS status CHAR(1) DEFAULT '0';
UPDATE sys_job SET status = '0' WHERE status IS NULL;

-- 移除已废弃的 invoke_target 列
ALTER TABLE sys_job DROP COLUMN IF EXISTS invoke_target;
