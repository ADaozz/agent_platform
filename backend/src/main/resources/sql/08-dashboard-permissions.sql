-- 已有库增量：仪表盘全局视角权限（若已重建 02 可跳过）
INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT 9, 'dashboard:view:all'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE permission_id = 9);

INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 1, 9
WHERE NOT EXISTS (SELECT 1 FROM public.sys_role_permission WHERE role_id = 1 AND permission_id = 9);
