-- 已有数据库增量：为 admin 角色补充 API Token 管理权限
INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 10, 'api:token:list'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 10);

INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 11, 'api:token:add'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 11);

INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 12, 'api:token:get'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 12);

INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 13, 'api:token:delete'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 13);

INSERT INTO sys_role_permission (role_id, permission_id)
SELECT 1, p.permission_id
FROM sys_permission p
WHERE p.permission_id IN (10, 11, 12, 13)
  AND NOT EXISTS (
      SELECT 1
      FROM sys_role_permission rp
      WHERE rp.role_id = 1
        AND rp.permission_id = p.permission_id
  );
