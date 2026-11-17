-- 初始管理员：admin/123456（密码 bcrypt）。仅当 sys_user 为空时插入。
-- 用 WHERE NOT EXISTS 而不是 INSERT OR IGNORE：运维改过账号/密码后重启不会再种回内置账号，
-- 删掉的测试账号也不会复活（见 deploy/scripts/set-admin.sh）。
INSERT INTO sys_user (user_id, user_name, pass_word, status, create_time, update_time)
SELECT 1001, 'admin', '$2b$10$UPiwFujaC3YD28nYRmDOtOipO5fdFzZNBGSHXDk1xX1h0JESl7hD2', '0', datetime('now'), datetime('now')
WHERE NOT EXISTS (SELECT 1 FROM sys_user);

INSERT OR IGNORE INTO sys_role (role_id, sys_role) VALUES
(1, 'admin'),
(2, 'user');

-- 清理已下线模块的权限 / 菜单（仪表盘、资产、定时任务、API Token）
DELETE FROM sys_role_permission
WHERE permission_id IN (
    SELECT permission_id FROM sys_permission
    WHERE sys_permission LIKE 'asset:%'
       OR sys_permission LIKE 'dashboard:%'
       OR sys_permission LIKE 'monitor:job:%'
       OR sys_permission LIKE 'api:token:%'
       OR sys_permission LIKE 'api:open:%'
);
DELETE FROM sys_permission
WHERE sys_permission LIKE 'asset:%'
   OR sys_permission LIKE 'dashboard:%'
   OR sys_permission LIKE 'monitor:job:%'
   OR sys_permission LIKE 'api:token:%'
   OR sys_permission LIKE 'api:open:%';
DELETE FROM sys_menu
WHERE path IN ('/dashboard', '/vm', '/app', '/monitor/job', '/system/token')
   OR menu_name IN ('仪表盘', '虚拟机', '应用服务', '定时任务', 'API 开放接口');

DROP TABLE IF EXISTS sys_job_log;
DROP TABLE IF EXISTS sys_job;
DROP TABLE IF EXISTS api_token;
DROP TABLE IF EXISTS vm_app;
DROP TABLE IF EXISTS vm_host;

-- 当前平台实际使用的权限（与前端路由 / 后端 @RequiresPermissions 对齐）
INSERT OR IGNORE INTO sys_permission (permission_id, sys_permission) VALUES
(1, 'system:user:list'),
(2, 'system:user:add'),
(3, 'system:user:edit'),
(4, 'system:user:delete'),
(5, 'system:role:list'),
(14, 'system:role:add'),
(15, 'system:role:edit'),
(16, 'system:role:delete'),
(20, 'system:session:list'),
(21, 'system:session:kick'),
(22, 'system:session:manage'),
(23, 'system:cert:mine'),
(24, 'system:cert:list'),
(25, 'system:cert:approve'),
(26, 'system:cert:revoke');

INSERT OR IGNORE INTO sys_user_role (user_id, role_id)
SELECT 1001, 1
WHERE EXISTS (SELECT 1 FROM sys_user WHERE user_id = 1001);

INSERT OR IGNORE INTO sys_role_permission (role_id, permission_id) VALUES
(1, 1), (1, 2), (1, 3), (1, 4), (1, 5),
(1, 14), (1, 15), (1, 16),
(1, 20), (1, 21), (1, 22), (1, 23), (1, 24), (1, 25), (1, 26),
(2, 20), (2, 21), (2, 23);

INSERT OR IGNORE INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible) VALUES
(4, '用户管理', 0, '/system/user', 'manage_accounts', 1, '0'),
(5, '角色管理', 0, '/system/role', 'shield_person', 2, '0'),
(8, '登录设备管理', 0, '/system/session', 'devices', 3, '0'),
(9, '我的证书', 0, '/system/cert/mine', 'badge', 4, '0'),
(10, '证书管理', 0, '/system/cert', 'verified_user', 5, '0');

UPDATE sys_menu SET order_num = 1 WHERE menu_id = 4;
UPDATE sys_menu SET order_num = 2 WHERE menu_id = 5;
UPDATE sys_menu SET order_num = 3 WHERE menu_id = 8;
UPDATE sys_menu SET order_num = 4 WHERE menu_id = 9;
UPDATE sys_menu SET order_num = 5 WHERE menu_id = 10;

UPDATE sys_permission SET menu_id = 4, perm_name = '用户查询' WHERE sys_permission = 'system:user:list';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户新增' WHERE sys_permission = 'system:user:add';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户编辑' WHERE sys_permission = 'system:user:edit';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户删除' WHERE sys_permission = 'system:user:delete';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色查询' WHERE sys_permission = 'system:role:list';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色新增' WHERE sys_permission = 'system:role:add';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色编辑' WHERE sys_permission = 'system:role:edit';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色删除' WHERE sys_permission = 'system:role:delete';
UPDATE sys_permission SET menu_id = 8, perm_name = '设备查询' WHERE sys_permission = 'system:session:list';
UPDATE sys_permission SET menu_id = 8, perm_name = '踢出设备' WHERE sys_permission = 'system:session:kick';
UPDATE sys_permission SET menu_id = 8, perm_name = '设备管理' WHERE sys_permission = 'system:session:manage';
UPDATE sys_permission SET menu_id = 9, perm_name = '我的证书' WHERE sys_permission = 'system:cert:mine';
UPDATE sys_permission SET menu_id = 10, perm_name = '证书查询' WHERE sys_permission = 'system:cert:list';
UPDATE sys_permission SET menu_id = 10, perm_name = '证书审批' WHERE sys_permission = 'system:cert:approve';
UPDATE sys_permission SET menu_id = 10, perm_name = '证书吊销' WHERE sys_permission = 'system:cert:revoke';
UPDATE sys_permission SET perm_name = sys_permission WHERE perm_name IS NULL OR perm_name = '';
