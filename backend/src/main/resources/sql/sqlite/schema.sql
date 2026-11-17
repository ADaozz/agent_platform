-- SQLite 本地库表（幂等，可重复执行）
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sys_user (
    user_id         INTEGER         NOT NULL PRIMARY KEY,
    user_name       VARCHAR(64)     NOT NULL,
    pass_word       VARCHAR(128)    NOT NULL,
    email           VARCHAR(128),
    status          CHAR(1)         DEFAULT '0',
    create_time     TEXT,
    update_time     TEXT,
    last_login_time TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_user_user_name ON sys_user (user_name);
CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_user_email ON sys_user (email);

CREATE TABLE IF NOT EXISTS sys_role (
    role_id     INTEGER         NOT NULL PRIMARY KEY,
    sys_role    VARCHAR(64)     NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_role_sys_role ON sys_role (sys_role);

CREATE TABLE IF NOT EXISTS sys_permission (
    permission_id   INTEGER         NOT NULL PRIMARY KEY,
    sys_permission  VARCHAR(128)    NOT NULL,
    menu_id         INTEGER,
    perm_name       VARCHAR(64)
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_permission_sys_permission ON sys_permission (sys_permission);
CREATE INDEX IF NOT EXISTS idx_sys_permission_menu_id ON sys_permission (menu_id);

CREATE TABLE IF NOT EXISTS sys_user_role (
    user_id     INTEGER     NOT NULL,
    role_id     INTEGER     NOT NULL,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS sys_role_permission (
    role_id         INTEGER     NOT NULL,
    permission_id   INTEGER     NOT NULL,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS sys_menu (
    menu_id   INTEGER      NOT NULL PRIMARY KEY,
    menu_name VARCHAR(64)  NOT NULL,
    parent_id INTEGER      DEFAULT 0,
    path      VARCHAR(128),
    icon      VARCHAR(64),
    order_num INTEGER      DEFAULT 0,
    visible   CHAR(1)      DEFAULT '0'
);

CREATE TABLE IF NOT EXISTS sys_login_session (
    session_id   VARCHAR(64)  NOT NULL PRIMARY KEY,
    user_id      INTEGER      NOT NULL,
    device_name  VARCHAR(128),
    login_ip     VARCHAR(64),
    user_agent   VARCHAR(512),
    login_time   TEXT,
    status       CHAR(1)      DEFAULT '0',
    revoke_time  TEXT,
    login_type   CHAR(1)      DEFAULT '0'
);

CREATE INDEX IF NOT EXISTS idx_login_session_user ON sys_login_session (user_id, status, login_time);

CREATE TABLE IF NOT EXISTS sys_oper_log (
    oper_id         INTEGER         NOT NULL PRIMARY KEY,
    title           VARCHAR(64),
    business_type   VARCHAR(32),
    method          VARCHAR(200),
    request_method  VARCHAR(16),
    operator_type   VARCHAR(32),
    oper_user_id    INTEGER,
    oper_url        VARCHAR(255),
    oper_ip         VARCHAR(128),
    oper_param      TEXT,
    json_result     TEXT,
    status          CHAR(1)         DEFAULT '0',
    error_msg       VARCHAR(2000),
    cost_time       INTEGER,
    oper_time       TEXT
);

CREATE INDEX IF NOT EXISTS idx_sys_oper_log_user ON sys_oper_log (oper_user_id);
CREATE INDEX IF NOT EXISTS idx_sys_oper_log_time ON sys_oper_log (oper_time);

CREATE TABLE IF NOT EXISTS sys_cert_apply (
    apply_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER      NOT NULL,
    user_name      VARCHAR(64),
    apply_type     VARCHAR(16)  NOT NULL DEFAULT 'new',
    status         VARCHAR(16)  NOT NULL DEFAULT 'pending',
    apply_reason   VARCHAR(512),
    reject_reason  VARCHAR(512),
    subject_cn     VARCHAR(128),
    subject_o      VARCHAR(128),
    subject_ou     VARCHAR(128),
    valid_days     INTEGER,
    approver_id    INTEGER,
    approve_time   TEXT,
    p12_password   VARCHAR(128),
    bundle_path    VARCHAR(512),
    create_time    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cert_apply_user ON sys_cert_apply (user_id, status);

CREATE TABLE IF NOT EXISTS sys_user_cert (
    cert_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER      NOT NULL,
    apply_id         INTEGER      NOT NULL,
    cert_type        VARCHAR(16)  NOT NULL,
    cert_fingerprint VARCHAR(128) NOT NULL,
    cert_serial      VARCHAR(64),
    subject_dn       VARCHAR(512),
    issuer_dn        VARCHAR(512),
    not_before       TEXT,
    not_after        TEXT,
    cert_path        VARCHAR(512),
    key_path         VARCHAR(512),
    p12_path         VARCHAR(512),
    status           CHAR(1)      DEFAULT '0',
    create_time      TEXT DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_user_cert_fp ON sys_user_cert (cert_fingerprint);
CREATE INDEX IF NOT EXISTS idx_user_cert_user ON sys_user_cert (user_id, cert_type, status);
