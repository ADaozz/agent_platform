-- 已有库增量：纠正 user 角色权限（仅 asset:vm:list、asset:app:list）
-- 若 user 能访问 /system/user，多半是 role_id=2 被误加了 system:user:list

DELETE FROM public.sys_role_permission
WHERE role_id = 2 AND permission_id IN (1, 2, 3, 4, 5, 7, 9);

INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 2, 6
WHERE NOT EXISTS (
    SELECT 1 FROM public.sys_role_permission WHERE role_id = 2 AND permission_id = 6
);

INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 2, 8
WHERE NOT EXISTS (
    SELECT 1 FROM public.sys_role_permission WHERE role_id = 2 AND permission_id = 8
);

-- 验证：user(1002) 登录后 permissions 应只有 asset:vm:list、asset:app:list
SELECT r.sys_role, p.sys_permission
FROM public.sys_role r
JOIN public.sys_role_permission rp ON r.role_id = rp.role_id
JOIN public.sys_permission p ON rp.permission_id = p.permission_id
WHERE r.role_id = 2
ORDER BY p.permission_id;
