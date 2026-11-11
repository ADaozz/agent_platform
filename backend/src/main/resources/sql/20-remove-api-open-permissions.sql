-- ============================================================
-- 步骤 20：移除 api:open:* 嵌套授权权限（已有库增量，可重复执行）
-- Token 开放能力改由代码控制：删/改仅允许操作 owner=当前用户 的数据
-- ============================================================

DELETE FROM sys_role_permission
WHERE permission_id IN (
    SELECT permission_id FROM sys_permission WHERE sys_permission LIKE 'api:open:%'
);

DELETE FROM sys_permission WHERE sys_permission LIKE 'api:open:%';

-- 执行后检查：应无 api:open:* 权限
SELECT permission_id, sys_permission, perm_name FROM sys_permission
WHERE sys_permission LIKE 'api:open:%';
