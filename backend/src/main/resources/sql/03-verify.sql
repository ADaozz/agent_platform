-- ============================================================
-- 步骤 3/3：验证数据（请先成功执行 01、02）
-- ============================================================

SELECT u.user_name, r.sys_role
FROM public.sys_user u
JOIN public.sys_user_role ur ON u.user_id = ur.user_id
JOIN public.sys_role r ON ur.role_id = r.role_id;

SELECT u.user_name, p.sys_permission
FROM sys_user u
JOIN sys_user_role ur ON u.user_id = ur.user_id
JOIN sys_role_permission rp ON ur.role_id = rp.role_id
JOIN sys_permission p ON rp.permission_id = p.permission_id
ORDER BY u.user_name, p.sys_permission;
