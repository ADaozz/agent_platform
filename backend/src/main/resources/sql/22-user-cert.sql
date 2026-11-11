-- ============================================================
-- 步骤 22：客户端证书申请/签发与登录方式（已有库增量，可重复执行）
-- ============================================================

ALTER TABLE public.sys_login_session ADD COLUMN IF NOT EXISTS login_type CHAR(1) DEFAULT '0';

CREATE TABLE IF NOT EXISTS public.sys_cert_apply (
    apply_id       BIGSERIAL PRIMARY KEY,
    user_id        BIGINT       NOT NULL,
    user_name      VARCHAR(64),
    apply_type     VARCHAR(16)  NOT NULL DEFAULT 'new',
    status         VARCHAR(16)  NOT NULL DEFAULT 'pending',
    apply_reason   VARCHAR(512),
    reject_reason  VARCHAR(512),
    subject_cn     VARCHAR(128),
    subject_o      VARCHAR(128),
    subject_ou     VARCHAR(128),
    valid_days     INTEGER,
    approver_id    BIGINT,
    approve_time   TIMESTAMP,
    p12_password   VARCHAR(128),
    bundle_path    VARCHAR(512),
    create_time    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cert_apply_user ON public.sys_cert_apply (user_id, status);

CREATE TABLE IF NOT EXISTS public.sys_user_cert (
    cert_id          BIGSERIAL PRIMARY KEY,
    user_id          BIGINT       NOT NULL,
    apply_id         BIGINT       NOT NULL,
    cert_type        VARCHAR(16)  NOT NULL,
    cert_fingerprint VARCHAR(128) NOT NULL,
    cert_serial      VARCHAR(64),
    subject_dn       VARCHAR(512),
    issuer_dn        VARCHAR(512),
    not_before       TIMESTAMP,
    not_after        TIMESTAMP,
    cert_path        VARCHAR(512),
    key_path         VARCHAR(512),
    p12_path         VARCHAR(512),
    status           CHAR(1)      DEFAULT '0',
    create_time      TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_user_cert_fp ON public.sys_user_cert (cert_fingerprint);
CREATE INDEX IF NOT EXISTS idx_user_cert_user ON public.sys_user_cert (user_id, cert_type, status);

-- 权限
INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:cert:mine'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:cert:mine');

INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:cert:list'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:cert:list');

INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:cert:approve'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:cert:approve');

INSERT INTO public.sys_permission (permission_id, sys_permission)
SELECT (SELECT COALESCE(MAX(permission_id), 0) + 1 FROM public.sys_permission), 'system:cert:revoke'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_permission WHERE sys_permission = 'system:cert:revoke');

INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 1, p.permission_id FROM public.sys_permission p
WHERE p.sys_permission IN ('system:cert:mine', 'system:cert:list', 'system:cert:approve', 'system:cert:revoke')
  AND NOT EXISTS (SELECT 1 FROM public.sys_role_permission rp WHERE rp.role_id = 1 AND rp.permission_id = p.permission_id);

INSERT INTO public.sys_role_permission (role_id, permission_id)
SELECT 2, p.permission_id FROM public.sys_permission p
WHERE p.sys_permission = 'system:cert:mine'
  AND NOT EXISTS (SELECT 1 FROM public.sys_role_permission rp WHERE rp.role_id = 2 AND rp.permission_id = p.permission_id);

INSERT INTO public.sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 9, '我的证书', 0, '/system/cert/mine', 'badge', 9, '0'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_menu WHERE menu_id = 9);

INSERT INTO public.sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 10, '证书管理', 0, '/system/cert', 'verified_user', 10, '0'
WHERE NOT EXISTS (SELECT 1 FROM public.sys_menu WHERE menu_id = 10);

UPDATE public.sys_permission SET menu_id = 9, perm_name = '我的证书' WHERE sys_permission = 'system:cert:mine';
UPDATE public.sys_permission SET menu_id = 10, perm_name = '证书查询' WHERE sys_permission = 'system:cert:list';
UPDATE public.sys_permission SET menu_id = 10, perm_name = '证书审批' WHERE sys_permission = 'system:cert:approve';
UPDATE public.sys_permission SET menu_id = 10, perm_name = '证书吊销' WHERE sys_permission = 'system:cert:revoke';
