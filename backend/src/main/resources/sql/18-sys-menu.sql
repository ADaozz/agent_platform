-- ============================================================
-- 步骤 18：菜单表与权限归属（已有库增量）
-- 菜单与权限分离：sys_menu 存菜单，sys_permission 通过 menu_id 挂到菜单下，
-- 供 GET /system/menu/permTree 组装角色授权树。
-- ============================================================

CREATE TABLE IF NOT EXISTS sys_menu (
    menu_id   BIGINT       NOT NULL PRIMARY KEY,
    menu_name VARCHAR(64)  NOT NULL,
    parent_id BIGINT       DEFAULT 0,
    path      VARCHAR(128),
    icon      VARCHAR(64),
    order_num INT          DEFAULT 0,
    visible   CHAR(1)      DEFAULT '0'
);

ALTER TABLE sys_permission ADD COLUMN IF NOT EXISTS menu_id   BIGINT;
ALTER TABLE sys_permission ADD COLUMN IF NOT EXISTS perm_name VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_sys_permission_menu_id ON sys_permission (menu_id);

-- ------------------------------------------------------------
-- 菜单种子数据：与前端 AppLayout.vue 的 allMenus 一一对应
-- ------------------------------------------------------------
INSERT INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 1, '仪表盘', 0, '/dashboard', 'dashboard', 1, '0'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE menu_id = 1);

INSERT INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 2, '虚拟机', 0, '/vm', 'dns', 2, '0'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE menu_id = 2);

INSERT INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 3, '应用服务', 0, '/app', 'apps', 3, '0'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE menu_id = 3);

INSERT INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 4, '用户管理', 0, '/system/user', 'manage_accounts', 4, '0'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE menu_id = 4);

INSERT INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 5, '角色管理', 0, '/system/role', 'shield_person', 5, '0'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE menu_id = 5);

INSERT INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 6, '定时任务', 0, '/monitor/job', 'schedule', 6, '0'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE menu_id = 6);

INSERT INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 7, 'API 开放接口', 0, '/system/token', 'key', 7, '0'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE menu_id = 7);

INSERT INTO sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
SELECT 8, '登录设备管理', 0, '/system/session', 'devices', 8, '0'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE menu_id = 8);

-- ------------------------------------------------------------
-- 回填权限的归属菜单与中文名（按权限标识匹配，不依赖 permission_id）
-- ------------------------------------------------------------
UPDATE sys_permission SET menu_id = 1, perm_name = '全局数据查看' WHERE sys_permission = 'dashboard:view:all';

UPDATE sys_permission SET menu_id = 2, perm_name = '虚拟机查询'   WHERE sys_permission = 'asset:vm:list';
UPDATE sys_permission SET menu_id = 2, perm_name = '虚拟机编辑'   WHERE sys_permission = 'asset:vm:edit';

UPDATE sys_permission SET menu_id = 3, perm_name = '应用查询'     WHERE sys_permission = 'asset:app:list';
UPDATE sys_permission SET menu_id = 3, perm_name = '应用编辑'     WHERE sys_permission = 'asset:app:edit';

UPDATE sys_permission SET menu_id = 4, perm_name = '用户查询'     WHERE sys_permission = 'system:user:list';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户新增'     WHERE sys_permission = 'system:user:add';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户编辑'     WHERE sys_permission = 'system:user:edit';
UPDATE sys_permission SET menu_id = 4, perm_name = '用户删除'     WHERE sys_permission = 'system:user:delete';

UPDATE sys_permission SET menu_id = 5, perm_name = '角色查询'     WHERE sys_permission = 'system:role:list';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色新增'     WHERE sys_permission = 'system:role:add';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色编辑'     WHERE sys_permission = 'system:role:edit';
UPDATE sys_permission SET menu_id = 5, perm_name = '角色删除'     WHERE sys_permission = 'system:role:delete';

UPDATE sys_permission SET menu_id = 6, perm_name = '任务查询'     WHERE sys_permission = 'monitor:job:list';
UPDATE sys_permission SET menu_id = 6, perm_name = '任务编辑'     WHERE sys_permission = 'monitor:job:edit';

UPDATE sys_permission SET menu_id = 7, perm_name = '令牌查询'     WHERE sys_permission = 'api:token:list';
UPDATE sys_permission SET menu_id = 7, perm_name = '令牌新增'     WHERE sys_permission = 'api:token:add';
UPDATE sys_permission SET menu_id = 7, perm_name = '令牌详情'     WHERE sys_permission = 'api:token:get';
UPDATE sys_permission SET menu_id = 7, perm_name = '令牌吊销'     WHERE sys_permission = 'api:token:delete';

UPDATE sys_permission SET menu_id = 8, perm_name = '设备查询'     WHERE sys_permission = 'system:session:list';
UPDATE sys_permission SET menu_id = 8, perm_name = '踢出设备'     WHERE sys_permission = 'system:session:kick';
UPDATE sys_permission SET menu_id = 8, perm_name = '设备管理'     WHERE sys_permission = 'system:session:manage';

-- 兜底：未维护中文名的权限用标识本身展示，避免树上出现空名节点
UPDATE sys_permission SET perm_name = sys_permission WHERE perm_name IS NULL OR perm_name = '';

-- 执行后检查：应返回 7 行菜单，且不存在 menu_id 为空的权限（否则会落到「未分类」节点）
SELECT menu_id, menu_name, order_num FROM sys_menu ORDER BY order_num;
SELECT permission_id, sys_permission, menu_id, perm_name FROM sys_permission WHERE menu_id IS NULL;
