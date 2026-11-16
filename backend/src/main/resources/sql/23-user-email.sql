-- ============================================================
-- 步骤 23：sys_user 增加邮箱列（自助注册邮箱验证码）
-- 已有库执行本文件；全新安装执行 01-create-tables.sql 即可
-- 注意：Kingbase 存在同名系统 catalog，必须限定 public schema
-- ============================================================

ALTER TABLE public.sys_user ADD COLUMN email VARCHAR(128);

-- 同一邮箱只允许注册一个账号（存量数据 email 为 NULL 不受影响）
CREATE UNIQUE INDEX uk_sys_user_email ON public.sys_user (email);
