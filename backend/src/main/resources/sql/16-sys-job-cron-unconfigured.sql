-- =============================================================================
-- 步骤 16：Cron 未配置占位改为空字符串（已有库增量）
-- 说明：0 0 0 * * ? 是合法的「每天 0 点」，不再当作未配置占位。
--       仅将仍为停用且 Cron 为旧默认值的记录视为历史占位并清空。
-- =============================================================================

ALTER TABLE sys_job ALTER COLUMN cron_expression SET DEFAULT '';

UPDATE sys_job
SET cron_expression = ''
WHERE enabled = '0'
  AND cron_expression = '0 0 0 * * ?';
