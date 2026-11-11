-- ============================================================
-- 步骤 4：业务表 — 虚机 vm_host、应用 vm_app
-- 依赖：01-create-tables.sql、02-insert-data.sql 已执行
-- ============================================================

DROP TABLE IF EXISTS vm_app;
DROP TABLE IF EXISTS vm_host;

CREATE TABLE vm_host (
    host_id           VARCHAR(36)     NOT NULL PRIMARY KEY,
    host_name         VARCHAR(128)    NOT NULL,
    os_type           VARCHAR(64)     NOT NULL,
    os_version        VARCHAR(64),
    vm_ip             VARCHAR(64),
    cpu_cores         INT,
    memory_gb         INT,
    disk_gb           INT,
    physical_host_ip  VARCHAR(64),
    lifecycle_status  VARCHAR(32)     NOT NULL DEFAULT 'creating',
    owner_user_id     BIGINT,
    network_zone      VARCHAR(16)     NOT NULL,
    env               VARCHAR(16)     NOT NULL,
    remark            VARCHAR(512),
    create_time       TIMESTAMP,
    update_time       TIMESTAMP,
    CONSTRAINT fk_vm_host_owner FOREIGN KEY (owner_user_id) REFERENCES sys_user (user_id)
);

CREATE TABLE vm_app (
    app_id        VARCHAR(36)     NOT NULL PRIMARY KEY,
    app_name      VARCHAR(128)    NOT NULL,
    host_id       VARCHAR(36)     NOT NULL,
    vm_ip         VARCHAR(64),
    deploy_path   VARCHAR(512)    NOT NULL,
    app_status    VARCHAR(16)     NOT NULL DEFAULT 'running',
    create_time   TIMESTAMP,
    update_time   TIMESTAMP,
    CONSTRAINT fk_vm_app_host FOREIGN KEY (host_id) REFERENCES vm_host (host_id),
    CONSTRAINT uk_vm_app_host_path UNIQUE (host_id, deploy_path)
);

CREATE UNIQUE INDEX uk_vm_host_name ON vm_host (host_name);
CREATE INDEX idx_vm_host_owner ON vm_host (owner_user_id);
CREATE INDEX idx_vm_host_lifecycle ON vm_host (lifecycle_status);
CREATE INDEX idx_vm_host_env ON vm_host (env);
CREATE INDEX idx_vm_host_network_zone ON vm_host (network_zone);
CREATE INDEX idx_vm_host_vm_ip ON vm_host (vm_ip);

CREATE INDEX idx_vm_app_host ON vm_app (host_id);
CREATE INDEX idx_vm_app_status ON vm_app (app_status);

-- lifecycle_status: creating | running | stopped | pending_delete | destroyed
-- network_zone:     idc | cfdc
-- env:              prod | dev | test
-- app_status:       running | stopped

SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('vm_host', 'vm_app')
ORDER BY table_name;
