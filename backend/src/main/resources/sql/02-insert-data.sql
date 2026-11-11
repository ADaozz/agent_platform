-- ============================================================
-- 步骤 2/3：插入测试数据（请先成功执行 01-create-tables.sql）
-- ============================================================

-- 密码均为 123456
INSERT INTO sys_user (user_id, user_name, pass_word, status, create_time, update_time) VALUES
(1001, 'admin', '$2b$10$UPiwFujaC3YD28nYRmDOtOipO5fdFzZNBGSHXDk1xX1h0JESl7hD2', '0', NOW(), NOW()),
(1002, 'user',  '$2b$10$UPiwFujaC3YD28nYRmDOtOipO5fdFzZNBGSHXDk1xX1h0JESl7hD2', '0', NOW(), NOW());

INSERT INTO public.sys_role (role_id, sys_role) VALUES
(1, 'admin'),
(2, 'user');

INSERT INTO public.sys_permission (permission_id, sys_permission) VALUES
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
(22, 'system:session:manage');

INSERT INTO public.sys_user_role (user_id, role_id) VALUES
(1001, 1),
(1002, 2);

INSERT INTO public.sys_role_permission (role_id, permission_id) VALUES
(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9),
(1, 10), (1, 11), (1, 12), (1, 13),
(1, 14), (1, 15), (1, 16), (1, 17), (1, 18), (1, 19),
(1, 20), (1, 21), (1, 22),
(2, 6), (2, 7), (2, 8), (2, 19), (2, 20), (2, 21);
-- user：asset + 登录设备查询/踢出；admin 另含 system:session:manage

-- 插入后检查
SELECT user_name FROM sys_user;
