-- 初始管理员：admin/123456（密码 bcrypt）。仅当 sys_user 为空时插入。
-- 用 WHERE NOT EXISTS 而不是 INSERT OR IGNORE：运维改过账号/密码后重启不会再种回内置账号，
-- 删掉的测试账号也不会复活（见 deploy/scripts/set-admin.sh）。
INSERT INTO sys_user (user_id, user_name, pass_word, status, create_time, update_time)
SELECT 1001, 'admin', '$2b$10$UPiwFujaC3YD28nYRmDOtOipO5fdFzZNBGSHXDk1xX1h0JESl7hD2', '0', datetime('now'), datetime('now')
WHERE NOT EXISTS (SELECT 1 FROM sys_user);

INSERT OR IGNORE INTO sys_role (role_id, sys_role) VALUES
(1, 'admin'),
(2, 'user');

INSERT OR IGNORE INTO sys_permission (permission_id, sys_permission) VALUES
(1, 'system:user:list'),
(2, 'system:user:add'),
(3, 'system:user:edit'),
(4, 'system:user:delete'),
(5, 'system:role:list'),
(6, 'asset:vm:list'),
(7, 'asset:vm:edit'),
(8, 'asset:app:list'),
(9, 'dashboard:view:all'),
(10, 'api:token:list'),
(11, 'api:token:add'),
(12, 'api:token:get'),
(13, 'api:token:delete'),
(14, 'system:role:add'),
(15, 'system:role:edit'),
(16, 'system:role:delete'),
(17, 'monitor:job:list'),
(18, 'monitor:job:edit'),
(19, 'asset:app:edit'),
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
(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9),
(1, 10), (1, 11), (1, 12), (1, 13),
(1, 14), (1, 15), (1, 16), (1, 17), (1, 18), (1, 19),
(1, 20), (1, 21), (1, 22), (1, 23), (1, 24), (1, 25), (1, 26),
(2, 6), (2, 7), (2, 8), (2, 19), (2, 20), (2, 21), (2, 23);

INSERT OR IGNORE INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible) VALUES
(1, '仪表盘', 0, '/dashboard', 'dashboard', 1, '0'),
(2, '虚拟机', 0, '/vm', 'dns', 2, '0'),
(3, '应用服务', 0, '/app', 'apps', 3, '0'),
(4, '用户管理', 0, '/system/user', 'manage_accounts', 4, '0'),
(5, '角色管理', 0, '/system/role', 'shield_person', 5, '0'),
(6, '定时任务', 0, '/monitor/job', 'schedule', 6, '0'),
(7, 'API 开放接口', 0, '/system/token', 'key', 7, '0'),
(8, '登录设备管理', 0, '/system/session', 'devices', 8, '0'),
(9, '我的证书', 0, '/system/cert/mine', 'badge', 9, '0'),
(10, '证书管理', 0, '/system/cert', 'verified_user', 10, '0');

UPDATE sys_permission SET menu_id = 1, perm_name = '全局数据查看' WHERE sys_permission = 'dashboard:view:all';
UPDATE sys_permission SET menu_id = 2, perm_name = '虚拟机查询' WHERE sys_permission = 'asset:vm:list';
UPDATE sys_permission SET menu_id = 2, perm_name = '虚拟机编辑' WHERE sys_permission = 'asset:vm:edit';
UPDATE sys_permission SET menu_id = 3, perm_name = '应用查询' WHERE sys_permission = 'asset:app:list';
UPDATE sys_permission SET menu_id = 3, perm_name = '应用编辑' WHERE sys_permission = 'asset:app:edit';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户查询' WHERE sys_permission = 'system:user:list';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户新增' WHERE sys_permission = 'system:user:add';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户编辑' WHERE sys_permission = 'system:user:edit';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户删除' WHERE sys_permission = 'system:user:delete';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色查询' WHERE sys_permission = 'system:role:list';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色新增' WHERE sys_permission = 'system:role:add';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色编辑' WHERE sys_permission = 'system:role:edit';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色删除' WHERE sys_permission = 'system:role:delete';
UPDATE sys_permission SET menu_id = 6, perm_name = '任务查询' WHERE sys_permission = 'monitor:job:list';
UPDATE sys_permission SET menu_id = 6, perm_name = '任务编辑' WHERE sys_permission = 'monitor:job:edit';
UPDATE sys_permission SET menu_id = 7, perm_name = '令牌查询' WHERE sys_permission = 'api:token:list';
UPDATE sys_permission SET menu_id = 7, perm_name = '令牌新增' WHERE sys_permission = 'api:token:add';
UPDATE sys_permission SET menu_id = 7, perm_name = '令牌详情' WHERE sys_permission = 'api:token:get';
UPDATE sys_permission SET menu_id = 7, perm_name = '令牌吊销' WHERE sys_permission = 'api:token:delete';
UPDATE sys_permission SET menu_id = 8, perm_name = '设备查询' WHERE sys_permission = 'system:session:list';
UPDATE sys_permission SET menu_id = 8, perm_name = '踢出设备' WHERE sys_permission = 'system:session:kick';
UPDATE sys_permission SET menu_id = 8, perm_name = '设备管理' WHERE sys_permission = 'system:session:manage';
UPDATE sys_permission SET menu_id = 9, perm_name = '我的证书' WHERE sys_permission = 'system:cert:mine';
UPDATE sys_permission SET menu_id = 10, perm_name = '证书查询' WHERE sys_permission = 'system:cert:list';
UPDATE sys_permission SET menu_id = 10, perm_name = '证书审批' WHERE sys_permission = 'system:cert:approve';
UPDATE sys_permission SET menu_id = 10, perm_name = '证书吊销' WHERE sys_permission = 'system:cert:revoke';
UPDATE sys_permission SET perm_name = sys_permission WHERE perm_name IS NULL OR perm_name = '';
