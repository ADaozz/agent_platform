-- ============================================================
-- 步骤 21：登录设备会话表与权限（已有库增量，可重复执行）
-- JWT 携带 jti=session_id；踢出即 status=1，下次请求 401
-- Kingbase：业务表须加 public. 前缀，避免与系统视图 sys_role 冲突
-- ============================================================

CREATE TABLE IF NOT EXISTS public.sys_login_session (
    session_id   VARCHAR(64)  NOT NULL PRIMARY KEY,
    user_id      BIGINT       NOT NULL,
    device_name  VARCHAR(128),
    login_ip     VARCHAR(64),
    user_agent   VARCHAR(512),
    login_time   TIMESTAMP,
    status       CHAR(1)      DEFAULT '0',
    revoke_time  TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_session_user ON public.sys_login_session (user_id, status, login_time);

-- 权限
INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:session:list'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:session:list');

INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:session:kick'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:session:kick');

INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:session:manage'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:session:manage');

-- admin + user：list / kick（用 role_id 常量，避免 JOIN public.sys_role 时误命中系统视图）
INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 1, p.permission_id
FROM public.sys_permission p
WHERE p.sys_permission IN ('system:session:list', 'system:session:kick')
  AND NOT EXISTS (
      SELECT 1 FROM public.sys_role_permission rp
      WHERE rp.role_id = 1 AND rp.permission_id = p.permission_id
  );

INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 2, p.permission_id
FROM public.sys_permission p
WHERE p.sys_permission IN ('system:session:list', 'system:session:kick')
  AND NOT EXISTS (
      SELECT 1 FROM public.sys_role_permission rp
      WHERE rp.role_id = 2 AND rp.permission_id = p.permission_id
  );

-- 仅 admin：manage
INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 1, p.permission_id
FROM public.sys_permission p
WHERE p.sys_permission = 'system:session:manage'
  AND NOT EXISTS (
      SELECT 1 FROM public.sys_role_permission rp
      WHERE rp.role_id = 1 AND rp.permission_id = p.permission_id
  );

-- 菜单
INSERT INTO public.sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 8, '登录设备管理', 0, '/system/session', 'devices', 8, '0'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_menu WHERE menu_id = 8);

UPDATE public.sys_permission SET menu_id = 8, perm_name = '设备查询' WHERE sys_permission = 'system:session:list';
UPDATE public.sys_permission SET menu_id = 8, perm_name = '踢出设备' WHERE sys_permission = 'system:session:kick';
UPDATE public.sys_permission SET menu_id = 8, perm_name = '设备管理' WHERE sys_permission = 'system:session:manage';

SELECT menu_id, sys_permission, perm_name FROM public.sys_permission
WHERE sys_permission LIKE 'system:session:%'
ORDER BY sys_permission;
