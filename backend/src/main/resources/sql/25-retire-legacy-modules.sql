-- ============================================================
-- 步骤 25：下线仪表盘 / 资产 / 定时任务 / API Token 模块
-- （可重复执行；与当前前端路由及后端接口对齐）
-- ============================================================

DELETE FROM public.sys_role_permission
WHERE permission_id IN (
    SELECT permission_id FROM public.sys_permission
    WHERE sys_permission LIKE 'asset:%'
       OR sys_permission LIKE 'dashboard:%'
       OR sys_permission LIKE 'monitor:job:%'
       OR sys_permission LIKE 'api:token:%'
       OR sys_permission LIKE 'api:open:%'
);

DELETE FROM public.sys_permission
WHERE sys_permission LIKE 'asset:%'
   OR sys_permission LIKE 'dashboard:%'
   OR sys_permission LIKE 'monitor:job:%'
   OR sys_permission LIKE 'api:token:%'
   OR sys_permission LIKE 'api:open:%';

DELETE FROM public.sys_menu
WHERE path IN ('/dashboard', '/vm', '/app', '/monitor/job', '/system/token')
   OR menu_name IN ('仪表盘', '虚拟机', '应用服务', '定时任务', 'API 开放接口');

-- 普通用户默认：登录设备查询/踢出 + 我的证书
INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.sys_role r
CROSS JOIN public.sys_permission p
WHERE r.sys_role IN ('user', '普通用户')
  AND p.sys_permission IN ('system:session:list', 'system:session:kick', 'system:cert:mine')
  AND NOT EXISTS (
      SELECT 1 FROM public.sys_role_permission rp
      WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id
  );

-- admin 补齐仍在使用的平台权限
INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.sys_role r
CROSS JOIN public.sys_permission p
WHERE r.sys_role = 'admin'
  AND p.sys_permission IN (
      'system:user:list', 'system:user:add', 'system:user:edit', 'system:user:delete',
      'system:role:list', 'system:role:add', 'system:role:edit', 'system:role:delete',
      'system:session:list', 'system:session:kick', 'system:session:manage',
      'system:cert:mine', 'system:cert:list', 'system:cert:approve', 'system:cert:revoke'
  )
  AND NOT EXISTS (
      SELECT 1 FROM public.sys_role_permission rp
      WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id
  );

DROP TABLE IF EXISTS public.sys_job_log;
DROP TABLE IF EXISTS public.sys_job;
DROP TABLE IF EXISTS public.api_token;
DROP TABLE IF EXISTS public.vm_app;
DROP TABLE IF EXISTS public.vm_host;
