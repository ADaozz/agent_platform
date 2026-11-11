-- ============================================================
-- 步骤 7：预留表（API Token、定时任务）— 实现业务逻辑前执行
-- ============================================================

-- TODO: 按 ApiTokenEntity / SysJobEntity / SysJobLogEntity 字段完善索引与约束

CREATE TABLE IF NOT EXISTS api_token (
    access_key    VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id       BIGINT          NOT NULL,
    token_name    VARCHAR(128)    NOT NULL,
    detail        VARCHAR(512)    NOT NULL,
    asset         TEXT            NOT NULL,
    secret_key    VARCHAR(1024)   NOT NULL,
    status        CHAR(1)         DEFAULT '0',
    expire_time   TIMESTAMP,
    create_time   TIMESTAMP,
    update_time   TIMESTAMP,
    CONSTRAINT fk_api_token_user FOREIGN KEY (user_id) REFERENCES sys_user (user_id)
);

CREATE INDEX IF NOT EXISTS idx_api_token_user ON api_token (user_id);
CREATE INDEX IF NOT EXISTS idx_api_token_status ON api_token (status);

CREATE TABLE IF NOT EXISTS sys_job (
    job_id          BIGINT          NOT NULL PRIMARY KEY,
    job_name        VARCHAR(128)    NOT NULL,
    bean_name       VARCHAR(64)     NOT NULL,
    job_group       VARCHAR(64)     DEFAULT 'DEFAULT',
    cron_expression VARCHAR(64)     NOT NULL DEFAULT '',
    status          CHAR(1)         DEFAULT '0',
    description     VARCHAR(512),
    enabled         CHAR(1)         DEFAULT '0',
    create_time     TIMESTAMP,
    update_time     TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_job_bean_name ON sys_job (bean_name);
CREATE INDEX IF NOT EXISTS idx_sys_job_enabled ON sys_job (enabled);

CREATE TABLE IF NOT EXISTS sys_job_log (
    log_id      BIGINT          NOT NULL PRIMARY KEY,
    job_id      BIGINT,
    job_name    VARCHAR(128),
    status      CHAR(1),
    message     VARCHAR(2000),
    start_time  TIMESTAMP,
    end_time    TIMESTAMP
);
