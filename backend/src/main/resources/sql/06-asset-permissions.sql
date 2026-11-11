-- 已有库增量：为 user 角色补充 asset:app:list（若已重建 02 可跳过）
INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT 8, 'asset:app:list'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE permission_id = 8);

INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 1, 8
WHERE NOT EXISTS (SELECT 1 FROM public.sys_role_permission WHERE role_id = 1 AND permission_id = 8);

INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 2, 8
WHERE NOT EXISTS (SELECT 1 FROM public.sys_role_permission WHERE role_id = 2 AND permission_id = 8);
