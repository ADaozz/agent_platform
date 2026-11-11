-- 已有数据库增量：为 admin 角色补充角色 CRUD 权限
INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 14, 'system:role:add'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 14);

INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 15, 'system:role:edit'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 15);

INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 16, 'system:role:delete'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 16);

INSERT INTO sys_role_permission (role_id, permission_id)
SELECT 1, p.permission_id
FROM sys_permission p
WHERE p.permission_id IN (14, 15, 16)
  AND NOT EXISTS (
      SELECT 1
      FROM sys_role_permission rp
      WHERE rp.role_id = 1
        AND rp.permission_id = p.permission_id
  );
