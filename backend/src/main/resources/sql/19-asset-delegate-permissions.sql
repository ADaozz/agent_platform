-- ============================================================
-- 步骤 19：资产平台权限整理（已有库增量，可重复执行）
-- asset:vm:edit / asset:app:edit 保留在虚拟机/应用菜单（平台内编辑能力）
-- 对外 Token 能力不再使用 api:open:* 嵌套授权，见 20-remove-api-open-permissions.sql
-- ============================================================

-- 1. 仅清理无用权限（勿删 edit；虚机无 add/delete 接口）
DELETE FROM sys_role_permission
WHERE permission_id IN (
    SELECT permission_id FROM sys_permission
    WHERE sys_permission IN (
        'asset:vm:add', 'asset:vm:delete',
        'asset:app:add', 'asset:app:delete'
    )
);

DELETE FROM sys_permission
WHERE sys_permission IN (
    'asset:vm:add', 'asset:vm:delete',
    'asset:app:add', 'asset:app:delete'
);

-- 2. 平台内编辑权限（虚拟机/应用菜单）
INSERT INTO sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM sys_permission), 'asset:vm:edit'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE sys_permission = 'asset:vm:edit');

INSERT INTO sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM sys_permission), 'asset:app:edit'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE sys_permission = 'asset:app:edit');

INSERT INTO sys_role_permission (role_id, permission_id)
SELECT 1, p.permission_id
FROM sys_permission p
WHERE p.sys_permission IN ('asset:vm:edit', 'asset:app:edit')
  AND NOT EXISTS (
      SELECT 1 FROM sys_role_permission rp
      WHERE rp.role_id = 1 AND rp.permission_id = p.permission_id
  );

UPDATE sys_permission SET menu_id = 2, perm_name = '虚拟机编辑' WHERE sys_permission = 'asset:vm:edit';
UPDATE sys_permission SET menu_id = 3, perm_name = '应用编辑'   WHERE sys_permission = 'asset:app:edit';

-- 3. 虚拟机/应用菜单：查询 + 编辑
UPDATE sys_permission SET menu_id = 2, perm_name = '虚拟机查询' WHERE sys_permission = 'asset:vm:list';
UPDATE sys_permission SET menu_id = 3, perm_name = '应用查询'   WHERE sys_permission = 'asset:app:list';

-- 执行后检查
SELECT menu_id, sys_permission, perm_name FROM sys_permission
WHERE sys_permission LIKE 'asset:%'
ORDER BY menu_id, sys_permission;
