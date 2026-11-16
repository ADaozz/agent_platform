-- ============================================================
-- 步骤 24：确保「普通用户」具备自助证书与登录设备权限，
-- 并为已注册但未分配角色的账号补上默认角色（可重复执行）
-- ============================================================

-- 权限（若不存在则创建）
INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:cert:mine'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:cert:mine');

INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:session:list'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:session:list');

INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:session:kick'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:session:kick');

-- 绑定到「普通用户」角色（role_id=2 或 sys_role 为 普通用户/user）
INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.sys_role r
CROSS JOIN public.sys_permission p
WHERE r.sys_role IN ('普通用户', 'user')
  AND p.sys_permission IN ('system:cert:mine', 'system:session:list', 'system:session:kick')
  AND NOT EXISTS (
      SELECT 1 FROM public.sys_role_permission rp
      WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id
  );

-- 已注册但没有任何角色的用户 → 补普通用户角色
INSERT INTO public.sys_user_role (user_id, role_id)
SELECT u.user_id, r.role_id
FROM public.sys_user u
CROSS JOIN LATERAL (
    SELECT role_id FROM public.sys_role
    WHERE sys_role IN ('普通用户', 'user')
    ORDER BY CASE sys_role WHEN '普通用户' THEN 0 WHEN 'user' THEN 1 ELSE 2 END
    LIMIT 1
) r
WHERE NOT EXISTS (SELECT 1 FROM public.sys_user_role ur WHERE ur.user_id = u.user_id)
  AND NOT EXISTS (
      SELECT 1 FROM public.sys_user_role ur2
      JOIN public.sys_role r2 ON r2.role_id = ur2.role_id
      WHERE ur2.user_id = u.user_id AND r2.sys_role = 'admin'
  );
