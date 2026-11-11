-- ============================================================
-- 步骤 1/3：建表（请先完整执行本文件，成功后再执行 02-insert-data.sql）
-- ============================================================

-- 如不确定当前 schema，可先执行：
-- SELECT current_database(), current_schema();

DROP TABLE IF EXISTS sys_role_permission;
DROP TABLE IF EXISTS sys_user_role;
DROP TABLE IF EXISTS sys_permission;
DROP TABLE IF EXISTS sys_role;
DROP TABLE IF EXISTS sys_user;

CREATE TABLE sys_user (
    user_id         BIGINT          NOT NULL PRIMARY KEY,
    user_name       VARCHAR(64)     NOT NULL,
    pass_word       VARCHAR(128)    NOT NULL,
    status          CHAR(1)         DEFAULT '0',
    create_time     TIMESTAMP,
    update_time     TIMESTAMP,
    last_login_time TIMESTAMP
);

CREATE TABLE sys_role (
    role_id     BIGINT          NOT NULL PRIMARY KEY,
    sys_role    VARCHAR(64)     NOT NULL
);

CREATE TABLE sys_permission (
    permission_id   BIGINT          NOT NULL PRIMARY KEY,
    sys_permission  VARCHAR(128)    NOT NULL
);

CREATE TABLE sys_user_role (
    user_id     BIGINT      NOT NULL,
    role_id     BIGINT      NOT NULL,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE sys_role_permission (
    role_id         BIGINT      NOT NULL,
    permission_id   BIGINT      NOT NULL,
    PRIMARY KEY (role_id, permission_id)
);

CREATE UNIQUE INDEX uk_sys_user_user_name ON sys_user (user_name);
CREATE UNIQUE INDEX uk_sys_role_sys_role ON sys_role (sys_role);
CREATE UNIQUE INDEX uk_sys_permission_sys_permission ON sys_permission (sys_permission);

-- 建表后立即检查（应返回 5 行）
SELECT table_name
FROM information_schema.tables
WHERE table_name IN (
    'sys_user', 'sys_role', 'sys_permission', 'sys_user_role', 'sys_role_permission'
)
ORDER BY table_name;
