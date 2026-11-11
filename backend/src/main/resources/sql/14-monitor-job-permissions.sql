-- 已有数据库增量：定时任务 monitor:job 权限（仅 list / edit，无 add / delete）
INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 17, 'monitor:job:list'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 17);

INSERT INTO sys_permission (permission_id, sys_permission)
SELECT 18, 'monitor:job:edit'
WHERE NOT EXISTS (SELECT 1 FROM sys_permission WHERE permission_id = 18);

INSERT INTO sys_role_permission (role_id, permission_id)
SELECT 1, p.permission_id
FROM sys_permission p
WHERE p.permission_id IN (17, 18)
  AND NOT EXISTS (
      SELECT 1
      FROM sys_role_permission rp
      WHERE rp.role_id = 1
        AND rp.permission_id = p.permission_id
  );
