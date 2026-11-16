# 部署与公网发布

单机裸部署：nginx 对外，Spring Boot 与 Agent Runtime 只监听回环，SQLite 落盘，Redis 存登录会话。
配置模板在 [`deploy/`](../deploy/) 下，本文说明依赖、步骤与边界。

```text
公网
 │  :80  → ACME 校验 / 301 到 443
 │  :443 → 前端静态资源 + /api 反向代理
 │  :8443→ 客户端证书登录（可选，只放行 /login/cert）
 ▼
nginx (root, 443/8443)
 │
 ├─ /api/** ─────────────► Spring Boot 127.0.0.1:8080   (JWT/Shiro 鉴权 + 签名网关)
 │                              │ HMAC 签名 + 用户身份
 │                              ▼
 └────────────────────────► agent-runtime 127.0.0.1:8090 (FastAPI，Bubblewrap 沙箱)
                                │
 Redis 127.0.0.1:6379 ◄────────┘ 登录会话 / 验证码 / API Token 缓存
 SQLite /var/lib/agent-platform/data/agent-platform.db
```

## 1. 依赖清单（按代码实际锁定版本核对）

### 后端（`backend/`）

| 依赖 | 实际要求 | 依据 |
| --- | --- | --- |
| **JDK 8**（运行 + 构建） | 1.8 | `pom.xml`：`java.version=1.8`，`maven-compiler-plugin` 显式 `<source>1.8</source><target>1.8</target>` |
| Spring Boot | 2.6.13 | `spring-boot.version`；该版本要求 Java 8+，官方支持到 17 |
| Lombok | 1.18.24（Boot BOM 决定） | Lombok 1.18.24 支持 JDK 8/11/17，**不支持 JDK 21+**，装 21/24 会编译失败 |
| Maven | 3.6+（仅构建） | 无 `mvnw`，需系统 Maven |
| sqlite-jdbc | 3.46.1.3 | 内嵌 SQLite 引擎，**不需要系统 sqlite 库**；`sqlite3` CLI 只用于运维 |
| 其他 | mybatis-plus 3.5.5、shiro 1.13.0、jjwt 0.11.5、bcpkix-jdk15on 1.70 | 全部 Java 8 兼容 |
| 金仓 4 个 jar | `lib/*.jar`，system scope | 走 `sqlite` profile 时不需要金仓实例；`includeSystemScope=true` 会打进 jar |

**结论：用 JDK 8，不要用 17/21 图省事。** 除了 Lombok 的兼容上限，运行时也别无收益——目标字节码是 1.8，
只是增加 IllegalAccess/反射相关的风险面。Ubuntu 22.04 与 24.04 的 `universe` 都有 `openjdk-8-jdk`。

### 前端（`frontEnd/`）

| 依赖 | 实际要求 | 依据 |
| --- | --- | --- |
| Node.js | `^22.18.0 \|\| >=24.12.0` | `package.json` → `engines`；Vite 8 / TypeScript 6 / Tailwind 4 / vue-tsc 3 |
| 运行时 | 不需要 Node | 构建产物是纯静态 `dist/`，由 nginx 直接发 |

> `agent-runtime/README.md` 里写的「Node.js 20.19+」已过期，以 `frontEnd/package.json` 的 `engines` 为准；
> 在 Node 20 上 `npm ci` 会直接报引擎不匹配。

### Agent Runtime（`agent-runtime/`）

| 依赖 | 实际要求 | 依据 |
| --- | --- | --- |
| Python | **3.12**（最低 3.11） | 逐包检查 `requirements.lock` 的 `Requires-Python`：118 个包里 17 个要求 ≥3.11（deepagents 0.7.32、starlette 1.10.0、sse-starlette 3.6.0、httpx2、websockets 17.3、pydantic-settings、wcmatch 等），最高要求就是 3.11 |
| 源码语法 | 3.10 可用 | 用 3.10 编译全部 `platform_app` 源码通过，版本下限由依赖而非语法决定 |
| Bubblewrap | `bwrap` 在 PATH，且允许非特权 user namespace | `agent_core/sandbox.py` 预检失败会直接报错，不会降级成宿主 shell |
| LibreOffice | 可选，`libreoffice` 在 PATH | DOCX/PPTX 正式分页渲染；建议同时装 `libreoffice-java-common`、`ure-java`、`default-jre-headless`，否则无头转 PDF 可能 `javaldx` / UNO 崩溃 |
| 字体 | 可选，`fonts-noto-cjk` | 中文文档渲染 |
| 编译期 | `build-essential`、`python3.12-dev` | 部分 wheel 缺失时需要本地编译 |

Ubuntu 22.04 自带 Python 3.10，需要 deadsnakes PPA（`install-host.sh` 自动处理）；24.04 自带 3.12。

### 基础服务

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| nginx | 任意带 `http_ssl_module` + `http_v2_module` 的版本（22.04 是 1.18） | 443 与 8443 都要求 SSL，`http2` 写在 `listen` 上 |
| redis-server | ≥6.0（22.04 是 6.0.16，24.04 是 7.0） | 只用到 `SET/GET/INCR` + TTL；必须 `maxmemory-policy noeviction` |
| sqlite3 CLI | 任意 | 仅备份/巡检用，运行时由 JDBC 内嵌引擎处理 |
| certbot | 任意 | 只签发/续期证书，续期钩子同步到 nginx 路径 |
| gettext-base | — | 提供 `envsubst`，渲染配置模板 |
| rsync、ufw | — | 发布同步、防火墙 |

### 服务器规格参考

| 项 | 最低 | 建议（≤10 人试用） |
| --- | --- | --- |
| CPU | 2 核 | 4 核（Agent 任务与文档渲染吃 CPU） |
| 内存 | 2 GB | 4 GB 以上（JVM + Python + LibreOffice） |
| 磁盘 | 20 GB | 50 GB SSD（workspace、checkpoint、文档产物会持续增长） |
| 系统 | Ubuntu 22.04 / 24.04 x86_64 | 同左 |

## 2. 安装

脚本按 Ubuntu / Debian（apt）编写，其他发行版需自行替换装包步骤。

```bash
# 仓库放到服务器上（或至少把 deploy/ 拷过去）
git clone <repo> /root/agent_platform && cd /root/agent_platform

sudo install -d -m 700 /etc/agent-platform
sudo cp deploy/deploy.env.example /etc/agent-platform/deploy.env
sudo editor /etc/agent-platform/deploy.env      # 至少改 DOMAIN / ACME_EMAIL

sudo deploy/scripts/install-host.sh
```

`install-host.sh` 做的事（幂等，可重复执行）：

1. 装包：nginx、redis-server、sqlite3、openjdk-8-jre-headless、bubblewrap、ufw、rsync、build-essential；
   `INSTALL_OFFICE=true` 追加 LibreOffice 与中文字体（68 个包，装完约 410MB），
   `INSTALL_BUILD_TOOLS=true` 追加 JDK 8 + Maven；
   Python 3.12 缺失时自动加 deadsnakes PPA。
2. 建 `agent-platform` 系统用户与 `deploy.env` 里声明的目录。
3. 生成 `/etc/agent-platform/secrets.env`（600）：JWT 密钥、HMAC 共享密钥、Redis 密码。**只生成一次**，
   丢失后所有登录态失效（数据不受影响）。
4. 写 `/etc/redis/agent-platform.conf`（AOF + noeviction + 危险命令改名），停用发行版 `redis-server`
   服务，改用 `redis-agent-platform.service`。
5. 写 nginx 站点（静态资源 + `/api` 反代 + SPA 回退）、签服务端证书（本地 CA 可用就由 CA 签，
   否则自签占位）、拼接客户端 CA bundle、渲染 8443 片段（`CERT_LOGIN_ENABLED=false` 时写空文件）。
6. 安装并启用两个 systemd 单元（此时还没有版本，不会启动服务）。
7. 开 ufw：只放行 22 与 443（域名模式再加 80 给 ACME，证书登录启用时加 8443）。
   8080/8090/6379 一律不放行，它们绑在回环上。

`deploy/` 会被复制到 `/opt/agent-platform/deploy/`，后续发布/备份都用服务器上这份。

内存调整：`/etc/agent-platform/backend.env` 里的 `JAVA_OPTS` 用 `-Xmx`（4GB 机器 `-Xmx2g`，8GB 用 `-Xmx4g`）。
JDK 8 **不支持** `-XX:MaxRAMPercentage`，写进去 JVM 会直接报 `Improperly specified VM option` 起不来。

## 3. 构建与发布

在构建机（需要 JDK 8 + Maven + Node ≥22.18）：

```bash
deploy/scripts/build-release.sh
# 产物：build/release-<时间戳>-<git短SHA>/  及其 .tar.gz
```

构建内容：`backend.jar`（`mvn -Dmaven.test.skip=true package`）、`frontend/`（`npm run build`，含 type-check）、
`runtime/`（agent-runtime 源码，排除 `.venv`、本地数据、测试）。

> 用 `-Dmaven.test.skip=true` 而不是 `-DskipTests`：`src/test` 里有 `Set.of()` 这类 Java 9+ API，
> JDK 8 下连测试**编译**都会失败（`skipTests` 只跳过执行）。纯后端构建同理。

传到服务器并发布：

```bash
scp build/release-*.tar.gz root@<server>:/tmp/
ssh root@<server> 'tar -C /tmp -xzf /tmp/release-<时间戳>-<SHA>.tar.gz'
ssh root@<server> 'sudo /opt/agent-platform/deploy/scripts/release.sh /tmp/release-<时间戳>-<SHA>'
```

`release.sh` 会：同步到 `releases/<版本>/` → 首次部署时创建 Python venv 并装 `requirements.lock` 与两个
Office Skill 依赖 → 原子切换 `current` 软链 → 重启两个服务 → 用 `healthcheck.sh` 轮询；失败自动切回上一版本。
保留最近 5 个版本。

## 4. 域名与 TLS

1. DNS A 记录指向服务器公网 IP，等待解析生效（`getent ahostsv4 $DOMAIN` 能看到本机 IP）。
2. 先演练再签发：

```bash
sudo deploy/scripts/issue-tls-cert.sh --dry-run
sudo deploy/scripts/issue-tls-cert.sh
```

脚本把证书复制到 `TLS_CERT` / `TLS_KEY`（nginx 引用的路径），并写入 certbot 部署钩子——
续期后自动同步并 `systemctl reload nginx`。不要让 nginx 直接引用 `/etc/letsencrypt/live/...`：
首签之前该路径不存在，nginx 会起不来。

想用自有证书：把 `TLS_CERT` / `TLS_KEY` 指到自己的文件，跳过本节，`systemctl reload nginx` 即可。

### 4.1 只用 IP 访问（没有域名）

`deploy.env` 里的 `DOMAIN` 可以直接填公网 IPv4（例如 `203.0.113.10`），脚本会自动切换成 IP 模式：

| 项 | 域名模式 | IP 模式 |
| --- | --- | --- |
| 证书 | Let's Encrypt（受信任） | **本地 CA 签发**（`install-host.sh` / `issue-tls-cert.sh --local-ca`，825 天，SAN=`IP:<addr>`），Let's Encrypt 不支持给 IP 签证书 |
| 浏览器 | 绿锁 | 导入一次 `ca/root/root-ca.crt` 后**也是绿锁**（443 与 8443 共用同一套信任） |
| 兜底 | — | 本地 CA 不可用（没跑 `init-ca.sh`）时回退自签，需点「高级 → 继续访问」 |
| HSTS | 1 年 | **自动关闭**：开着 HSTS 时浏览器会记住"只走 HTTPS"，之后连"继续访问"都不给点，等于锁死站点 |
| 80 端口 | ACME 校验 + 301 | 只做 301（没有 ACME 可校验） |
| 8443 证书登录 | 可用 | 可用（客户端证书同样由本地 CA 签发，客户端只需信任同一个根 CA） |

重签服务端证书（比如换了 IP、或证书快过期）：

```bash
sudo deploy/scripts/issue-tls-cert.sh --local-ca    # 用本地 CA 重签（推荐，IP 模式默认行为）
sudo deploy/scripts/issue-tls-cert.sh --self-signed # 本地 CA 不可用时自签兜底
```

`--local-ca` 签出的 `fullchain.pem` = 叶子 + 中间 CA，**不含根 CA**（根 CA 由客户端预先导入）。
所以客户端要做的事只有一件：把 `ca/root/root-ca.crt` 导入「受信任的根证书颁发机构」。

> 公网 IP 变了（家庭宽带重播、运营商回收）就要重签一次，否则浏览器会因为证书 SAN 不匹配直接拒绝。
> 想避开这事，最终还是得上域名。

## 5. 首次登录与唯一管理员

`sql/sqlite/data.sql` 只在 `sys_user` **为空**时种一个 `admin/123456`（用 `WHERE NOT EXISTS`，
不是 `INSERT OR IGNORE`）。这意味着：改过账号、删过用户之后，重启**不会**把内置账号种回来。

公网上线前用 `set-admin.sh` 一步收敛成唯一管理员（会停后端、改库、再拉起）：

```bash
# 参数也可写在 deploy.env 的 ADMIN_USERNAME / ADMIN_PASSWORD
sudo deploy/scripts/set-admin.sh --user ADaozz --password '你的密码'
```

它做的事：

| 步骤 | 说明 |
| --- | --- |
| 删账号 | 删除除目标账号外的所有 `sys_user`，连带 `sys_user_role`、`api_token`、`sys_login_session`、`sys_cert_apply`、`sys_user_cert` |
| 保资产 | `vm_host.owner_user_id` 转给新管理员，不删资产 |
| 建/改账号 | 目标账号不存在就建，存在就重置密码并确保 `admin` 角色 |
| 留审计 | `sys_oper_log` 原样保留 |
| 收尾 | 打印当前账号表；`--keep-others` 可跳过删除 |

密码用 `python3-bcrypt`（`install-host.sh` 已装）生成 `$2b$10$` 哈希，与后端
`BCryptPasswordEncoder` 一致。**跑完把 `deploy.env` 里的 `ADMIN_PASSWORD` 清空。**

不需要自助注册时，在 nginx 站点里精确拦住注册接口，再 reload：

```bash
#    location = /api/register        { return 404; }
#    location = /api/register/code   { return 404; }
sudo systemctl reload nginx
```

同时检查：`sys_user.email` 是否需要换绑定、SMTP 是否可用，否则邮箱验证码注册会失败（不影响账密登录）。
发件账号在 `deploy.env` 的 `MAIL_USERNAME` / `MAIL_PASSWORD` 里填（163 用客户端授权码，不是登录密码），
`install-host.sh` 会写进 `secrets.env`（600）；已经在跑的机器改了 `deploy.env` 后重跑一次 `install-host.sh` 即可同步。

另外确认系统时间准确（`timedatectl status` 显示 `System clock synchronized: yes`）：
Agent Runtime 的 HMAC 签名只接受 ±30 秒的时间偏差，时钟漂移会导致 `/agent` 全部 401。

## 6. 证书登录（8443）边界

启用条件（后端启动即校验，缺一项直接失败）：

```bash
CERT_LOGIN_ENABLED=true
CERT_LOGIN_TRUSTED_PROXIES=127.0.0.1,::1
CERT_LOGIN_PUBLIC_ORIGIN=https://<域名或 IP>   # 必须是精确 Origin：无端口、无路径、带 https://
CERT_LOGIN_ALLOWED_ORIGINS=https://<域名或 IP>,https://localhost
SERVER_ADDRESS=127.0.0.1
```

> WSL / 本机用 `https://localhost` 打开时，**allowed-origins 必须包含 `https://localhost`**。
> #7 之后回跳不再用请求 Host；缺了 localhost 会 302 到 `PUBLIC_ORIGIN`（公网 IP），
> 本机访问表现为「点证书登录后跳转卡住、也不弹选证框」。

开启步骤（一套 CA 已经在 `/etc/agent-platform/ca` 的前提下）：

```bash
sudo deploy/scripts/init-ca.sh                    # 没有 CA 时先生成
# deploy.env 里把 CERT_LOGIN_ENABLED 改成 true，再重跑安装（会渲染 8443 片段并放行 8443/tcp）
sudo deploy/scripts/install-host.sh
sudo systemctl restart agent-platform-backend     # 日志出现「中间 CA 已加载」
sudo deploy/scripts/healthcheck.sh                # 多出 2 项 8443 检查
```

> **IP 模式下 `CERT_LOGIN_PUBLIC_ORIGIN` 填公网 IP 也能通过校验**（`isExactHttpsOrigin` 接受 IP，
> 只要求 https + 无路径）。代价是 IP 一变后端就启动失败（fail closed），必须同步改这里并重签证书。

nginx 侧边界（模板已实现）：

- **443 不启用 mTLS**，并显式清空 `X-Client-*`，防止外部伪造身份头；
- **8443 只把 nginx 自己解析出的 `$ssl_client_*` 写进请求头**，且只放行 `= /login/cert`，其余路径 404，
  不会变成通用代理；
- 使用 `ssl_verify_client optional_no_ca`：链校验交给后端按「已签发证书指纹 + 绑定关系」判定。

需要客户端 CA 材料：

```text
/etc/agent-platform/ca/root-ca.crt
/etc/agent-platform/ca/intermediate-ca.crt
/etc/agent-platform/ca/intermediate-ca.key     # 640 root:agent-platform，签发客户端证书用
/etc/agent-platform/tls/client-ca-bundle.crt   # nginx ssl_client_certificate
```

`install-host.sh` 会从 `CA_SOURCE_DIR`（或仓库里的 `ca/`）拷公钥，并**每次重新拼装**
`client-ca-bundle.crt`。私钥不在仓库里（`.gitignore` 的 `*.key`）：没有私钥时只能验证已有证书、
不能签发新证书，用 `init-ca.sh` 生成一套（见 §6.1）。无法确保这条边界时，保持 `CERT_LOGIN_ENABLED=false`。

实测行为（nginx 8443 → 后端，JDK 8 + Spring Boot 2.6）：

| 请求 | 结果 |
| --- | --- |
| 不带客户端证书 `GET /login/cert` | `200`，返回自动提交表单；后端 `verify=NONE` 不认 |
| 带未绑定证书 `POST /login/cert?redirect=0` | `500` `客户端证书未绑定或未签发` |
| 带未绑定证书 `POST /login/cert?redirect=1` | `302` → `https://<origin>/login?certError=证书登录失败` |
| 带已绑定证书 `POST /login/cert?redirect=0` | `200` + `token`，`user.roles` 为 `admin` |
| 带已绑定证书 `POST /login/cert?redirect=1` | `302` → `https://<origin>/login#certLogin=<base64>` |
| 8443 上任何非 `/login/cert` 路径 | `404` |

Windows 证书存储只发叶子证书、不带中间链，nginx 用 `ssl_client_certificate` 的 bundle 补链后
`X-Client-Verify: SUCCESS`，不需要客户端额外配置。

### 6.1 没有 CA 私钥：现生成一套

仓库 `ca/` 里只有 `root-ca.crt` / `intermediate-ca.crt`（公钥），没有签发用的私钥。
要启用证书登录并能在页面里申请证书，就需要中间 CA 私钥。可以生成一套新的：

```bash
sudo deploy/scripts/init-ca.sh                    # 生成 root + intermediate
sudo deploy/scripts/init-ca.sh --force            # 已有 CA 时重建（旧材料自动备份）
sudo deploy/scripts/init-ca.sh --with-server-cert # 顺带重签本地 CN=localhost 服务端证书
```

产物：

| 路径 | 内容 | 权限 |
| --- | --- | --- |
| `/etc/agent-platform/ca/root-ca.key` | 根 CA 私钥，只用于重签中间 CA | 600 root |
| `/etc/agent-platform/ca/intermediate-ca.key` | **签发客户端证书的私钥** | 640 root:agent-platform |
| `/etc/agent-platform/ca/root-ca.crt` | 根 CA 证书（10 年） | 644 |
| `/etc/agent-platform/ca/intermediate-ca.crt` | 中间 CA 证书（5 年，pathlen:0） | 644 |
| `ca/root/root-ca.crt`、`ca/intermediate/intermediate-ca.crt` | 公钥回写仓库，`install-host.sh` 从这里拼 `client-ca-bundle.crt` | 644 |

DN 与仓库原有 CA 一致（`O=personalDemo`、`CN=personalDemo Intermediate CA`），所以
`backend/docs/DEVELOPMENT.md` 里那些 Chrome/Edge 自动选证 `.reg` 规则不用改。

**换 CA 意味着旧根作废**：所有导入过旧 `root-ca.crt` 的浏览器都要换成新的，已经签发的客户端证书
全部失效。所以：

1. 用 `--force` 重建后，让用户重新导入新的 `root-ca.crt`（受信任的根证书颁发机构）；
2. `intermediate-ca.key` 与 `root-ca.key` 一定要离线备份——丢了 key 就只能再换一次 CA；
3. 重建后重启后端：`sudo systemctl restart agent-platform-backend`，日志应出现
   `中间 CA 已加载: /etc/agent-platform/ca/intermediate-ca.crt`。

`/etc/nginx/snippets/` 下的 `client-ca-bundle.crt` 由 `install-host.sh` **每次重新生成**
（`intermediate` + `root` 拼接），所以换 CA 后再跑一次 `install-host.sh` 即可，不会残留旧 bundle
导致所有客户端证书验链失败。Windows/macOS 的证书存储只发叶子证书、不带中间链，nginx 会用这个
bundle 自行补链，实测 `X-Client-Verify: SUCCESS`，不需要客户端额外配置。

`X-Client-Verify` 必须是 `SUCCESS` 后端才会用它（`X509CertUtils.parseClientCertFromRequest`），
而是否放行还取决于证书指纹是否已在页面里绑定，所以链验证通过 ≠ 能登录。

IP 模式下 8443 同样可用：服务端证书与客户端证书都由同一套本地 CA 签发，客户端只要信任
`ca/root/root-ca.crt` 一次，443 绿锁和 8443 选证就都正常。唯一要注意的是**重签服务端证书**
（换 IP 时）别用 `--self-signed`，否则 443 会退回不受信任状态。

## 7. 备份与回滚

```bash
sudo deploy/scripts/backup.sh                 # 默认 /var/backups/agent-platform，保留 14 天
```

备份内容：SQLite 平台库（`.backup`，先 `wal_checkpoint(TRUNCATE)`）、`certs/` 与 `runtime/`
（模型密钥、会话 checkpoint、workspace）、`/etc/agent-platform`（含 `secrets.env`）。
**产物含密钥，异地存放前先加密。**

回滚：

```bash
sudo ls /opt/agent-platform/releases
sudo ln -sfn /opt/agent-platform/releases/<上一版本> /opt/agent-platform/current
sudo systemctl restart agent-platform-backend agent-platform-runtime
sudo deploy/scripts/healthcheck.sh
```

数据回滚：先停两个服务，用备份覆盖 `agent-platform.db` 与 `runtime/`，再启动。

建议的定时任务：

```cron
15 3 * * * root /opt/agent-platform/deploy/scripts/backup.sh >/var/log/agent-platform-backup.log 2>&1
```

## 8. 公网暴露清单

必须只监听回环、且**不要**在云安全组/防火墙里放行：

| 端口 | 服务 | 期望监听 |
| --- | --- | --- |
| 8080 | Spring Boot | `127.0.0.1:8080` |
| 8090 | Agent Runtime | `127.0.0.1:8090` |
| 6379 | Redis | `127.0.0.1:6379`（+requirepass） |
| 22 | SSH | 全域，建议限制来源 IP |

对外只开 80 / 443，证书登录额外开 8443。**不要**把 8080 直接放出去：它绑在回环上，
而且明文 HTTP 传输 JWT/Cookie、绕过 nginx 的 `X-Client-*` 清理与安全响应头，
"后端有鉴权"不能替代 TLS。IP 模式（无 ACME）连 80 都可以不开，只留 443。

Windows 侧同理，只映射需要的端口：

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows\portproxy.ps1 -Ports 443
```

发布后自查：

```bash
ss -ltnp | grep -E '8080|8090|6379'      # 全部应是 127.0.0.1
sudo deploy/scripts/healthcheck.sh
curl -sS -o /dev/null -w '%{http_code}\n' https://<域名>/                  # 200
curl -sS -o /dev/null -w '%{http_code}\n' -H 'X-Client-Verify: SUCCESS' \
     -H 'X-Client-Cert: forged' https://<域名>/api/user/info               # 401，伪造头无效
```

其他基线：只装必要软件包；`secrets.env`、Redis 配置、`/etc/agent-platform` 保持 600/640；
开启 `unattended-upgrades` 或定期更新；`journalctl -u agent-platform-backend` 与
`/var/log/nginx/` 做日志轮转（发行版默认已含）。

## 9. 常见故障

| 现象 | 排查 |
| --- | --- |
| 后端起不来，日志 `cert.login.* 未配置` | `CERT_LOGIN_ENABLED=true` 时必须同时给 `CERT_LOGIN_PUBLIC_ORIGIN`（HTTPS）与可信代理 |
| `unable to open database file` | `/var/lib/agent-platform/data` 属主应为 `agent-platform`；systemd 里 `ProtectSystem=full` 只放开 `ReadWritePaths` |
| 页面能开但接口 502 | `curl 127.0.0.1:8080/login/cert/availability`；再查 `journalctl -u agent-platform-backend -n 100` |
| SSE 断流 / 事件延迟 | 必须走 `/api/agent-runtime/` 这条 location（`proxy_buffering off`、`proxy_read_timeout 1d`） |
| 登录后立刻掉线 | Redis 未启动或密码不一致：`REDISCLI_AUTH=... redis-cli ping`；`secrets.env` 与 Redis 配置必须同源 |
| 文档渲染失败 | 未装 LibreOffice/字体（`INSTALL_OFFICE=true`），或沙箱不可用。排版检查若报 `javaldx` / `UnoRuntimeException`，再装：`libreoffice-java-common ure-java default-jre-headless` |
| 右侧预览空白 / `/api/features` 里 docx·pptx 为 `enabled:false` + `ModuleNotFoundError` | 生产 venv 缺 Office Skill 依赖。`release.sh` 每次都会核对；也可手动：<br>`sudo /opt/agent-platform/venv/bin/pip install -r current/runtime/docx-ooxml-skill/requirements.txt -r current/runtime/pptx-ooxml-skill/requirements.txt && sudo systemctl restart agent-platform-runtime` |
| 点预览后文档目录为空 `[]` | 依赖缺失时生成的 docx/pptx 往往未进入预览目录；装好依赖后让 Agent **重新生成**，或下载查看。预览面板只在 Agent 对话页保留，切菜单/新建对话会自动收起 |
| 沙箱报 `bwrap preflight failed` | 先看异常里的 `exit code` 与 bwrap 原文：<br>`Address family not supported by protocol` → unit 的 `RestrictAddressFamilies` 少了 **AF_NETLINK**（bwrap 拉 lo 要 NETLINK_ROUTE），这是默认坑<br>`Operation not permitted` / `unprivileged user namespaces are not enabled` → `sysctl kernel.unprivileged_userns_clone` 或 AppArmor<br>`Can't bind mount X: No such file` → X 这个源码路径不存在 |
| 审批签发报「中间 CA 未加载 / 文件不存在」 | `/etc/agent-platform/ca` 曾是 `700 root:root`，服务用户穿不过去。应为 `750 root:agent-platform`，`intermediate-ca.key` 为 `640 root:agent-platform`；改完后 `systemctl restart agent-platform-backend`，日志应出现「中间 CA 已加载」 |
| 无痕 `cert-check` 为 SUCCESS，普通窗口证书登录失败 | 8443 若开了 `ssl_session_cache`，optional 下首次未交证后会复用无证会话，一直 `verify=NONE`。8443 必须 `ssl_session_cache off` + `ssl_session_tickets off`；客户端仍要**完全退出 Chrome** 清本地 TLS 会话后再试 |
| 证书登录选证后失败 / SSL 错误 | **登录只用 `sign.p12`**（客户端身份验证）。选成 `encrypt.p12` 会失败。Windows 可用 `ca_test/list-client-certs.ps1` 核对；本机调试可用 `ca_test/*-autoselect-localhost.reg` |
| `https://localhost` 证书登录卡住 | `CERT_LOGIN_ALLOWED_ORIGINS` 必须含 `https://localhost`；后端对 localhost 有硬编码放行，但代理头与 nginx 仍要配对。勿依赖请求 Host 回跳 |
| 上传 413 | nginx `client_max_body_size`（模板 220m）与单文件 20MB×10 的上限对齐 |

## 10. WSL2 作为对外服务器（Windows 端口转发）

本套件可以直接跑在 WSL2 里，但有三件事必须在 Windows 侧做对。

### 10.1 先确认 systemd

三个服务都由 systemd 单元托管。在普通 WSL 终端里：

```bash
systemctl is-system-running        # 期望 running / degraded，不是 offline
```

不是 running 就在 `/etc/wsl.conf` 里加：

```ini
[boot]
systemd=true
```

然后 PowerShell 执行 `wsl --shutdown`，重新打开 WSL。`install-host.sh` 会检查 PID 1，不是 systemd 会直接报错退出。

### 10.2 端口怎么出去

WSL 内 nginx 仍监听 `80 / 443 / 8443`（root 启动，和裸机一致），区别只在 Windows 到 WSL 这一段：

- **推荐（Windows 11 23H2+）**：`%UserProfile%\.wslconfig` 写 `[wsl2]` + `networkingMode=mirrored`，
  镜像网络下 WSL 直接占用 Windows 端口，不需要 portproxy。
- **NAT 模式（默认）**：用 `deploy/windows/portproxy.ps1`（管理员 PowerShell）：

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows\portproxy.ps1
# 想让它自己跟着 WSL IP 变化刷新：
powershell -ExecutionPolicy Bypass -File deploy\windows\portproxy.ps1 -EveryMinutes 5
# 清理：
powershell -ExecutionPolicy Bypass -File deploy\windows\portproxy.ps1 -Remove
```

脚本按当前 WSL IP 建立 `0.0.0.0:80/443/8443 → <WSL_IP>:同端口` 的 portproxy，并建对应的入站防火墙规则。
WSL2 的 IP 每次重启都会变，所以 NAT 模式下必须重复执行（或挂计划任务）。

> `portproxy.ps1` 未在本机实测（当前无 Windows 环境），执行前请先看清端口列表与现有规则。

### 10.3 上游两跳都要通

```text
公网 :443 → 路由器 NAT → Windows 主机 :443 (portproxy) → WSL2 :443 (nginx)
```

- 路由器把 80 / 443（证书登录再要 8443）转发到 Windows 主机的内网 IP；
- 域名 A 记录指向**公网出口 IP**，不是 WSL 的内网地址；
- Let's Encrypt 用 80 端口校验，链路任何一跳没通，`issue-tls-cert.sh` 都会失败；
- ufw 在 WSL2 里常因缺 netfilter 模块启不来（安装脚本只告警不中断），真正的边界是
  Windows 防火墙与路由器规则。

### 10.4 WSL 特有的坑

| 现象 | 原因与处理 |
| --- | --- |
| 重启 Windows 后站点全挂 | WSL 实例没启动，systemd 服务自然不会跑。用「任务计划程序」在登录时执行 `wsl -d <发行版> -u root echo ok` 拉起实例 |
| `wsl --shutdown` 后需要重新发布 | 正常：数据在磁盘上，实例起来后 systemd 会自动拉起三个服务 |
| Agent 对话全部 401 | 休眠/长时间挂起后 WSL 时钟漂移，HMAC 只容忍 ±30 秒：`sudo hwclock -s` 或 `wsl --shutdown` 重开 |
| 日志里刷 `Clock moved backwards` / `操作日志落库失败` | 同上，WSL 校正时钟时会瞬间回拨，后端雪花 ID 生成器在回拨期间拒绝发号；只影响操作日志落库（WARN，不影响业务）。时钟追平后自愈，根治办法是装 `systemd-timesyncd` 并保持 WSL 常驻 |
| 后端启动失败 `unable to open database file` | WSL 里把数据放到 `/mnt/c`、`/mnt/d`（DrvFs）会拿不到 WSL 需要的权限与 WAL 语义，必须放 Linux 根文件系统（默认 `/var/lib`） |
| 首屏很慢 | dist 有 62MB（字体 + three.js），确认 nginx 开了 `gzip`，且 Windows 侧没有二次代理 |
