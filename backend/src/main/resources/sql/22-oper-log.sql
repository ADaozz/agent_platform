-- ============================================================
-- 步骤 22：操作日志表（Skeleton v1.0）— 已有库增量执行
-- ============================================================

CREATE TABLE IF NOT EXISTS public.sys_oper_log (
    oper_id         BIGINT          NOT NULL PRIMARY KEY,
    title           VARCHAR(64),
    business_type   VARCHAR(32),
    method          VARCHAR(200),
    request_method  VARCHAR(16),
    operator_type   VARCHAR(32),
    oper_user_id    BIGINT,
    oper_url        VARCHAR(255),
    oper_ip         VARCHAR(128),
    oper_param      TEXT,
    json_result     TEXT,
    status          CHAR(1)         DEFAULT '0',
    error_msg       VARCHAR(2000),
    cost_time       BIGINT,
    oper_time       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sys_oper_log_user ON public.sys_oper_log (oper_user_id);
CREATE INDEX IF NOT EXISTS idx_sys_oper_log_time ON public.sys_oper_log (oper_time);
