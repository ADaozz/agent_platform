# deploy/

生产部署套件（单机裸部署：nginx + Spring Boot + FastAPI + SQLite + Redis）。
完整说明见 [docs/DEPLOY.md](../docs/DEPLOY.md)。

| 路径 | 用途 |
| --- | --- |
| `deploy.env.example` | 部署参数模板 → `/etc/agent-platform/deploy.env` |
| `env/*.template` | 两个服务的环境变量 → `/etc/agent-platform/*.env` |
| `nginx/*.template` | 站点与 8443 证书登录片段 |
| `redis/*.template` | Redis 实例配置（AOF、noeviction） |
| `systemd/*.template` | 后端、运行时、Redis 三个单元 |
| `scripts/install-host.sh` | 首次安装（root，幂等） |
| `scripts/build-release.sh` | 构建 jar + 前端 + 运行时源码 |
| `scripts/release.sh` | 服务器上原子发布与失败回滚 |
| `scripts/set-admin.sh` | 收敛成唯一管理员：删其它账号、重置密码、转移资产归属 |
| `scripts/init-ca.sh` | 生成客户端证书 CA（root + intermediate），私钥落 `/etc`，公钥回写 `ca/` |
| `scripts/issue-tls-cert.sh` | Let's Encrypt 签发与续期钩子；`--local-ca` 用本地 CA 重签服务端证书（IP 模式默认），`--self-signed` 自签兜底 |
| `scripts/backup.sh` | SQLite + 数据 + 配置备份 |
| `scripts/healthcheck.sh` | 发布后与定时巡检 |
| `windows/portproxy.ps1` | **Windows 上**（管理员 PS）：把 443/8443 转发进 WSL，NAT 模式必须 |
| `windows/wsl-proxy.ps1` | **Windows 上**（管理员 PS）：把本机代理端口桥接给 WSL（`-Port 12450`） |

`DOMAIN` 填域名或公网 IPv4 都可以：填 IP 时自动改用自签证书（397 天，SAN=`IP:<addr>`）、关闭 HSTS、
ufw 只开 22/443（`CERT_LOGIN_ENABLED=true` 再自动加 8443/tcp），详见 [docs/DEPLOY.md §4.1](../docs/DEPLOY.md)。

首次安装之后的常规操作：

```bash
sudo deploy/scripts/release.sh /path/to/release-<版本>
sudo deploy/scripts/set-admin.sh                 # 读 deploy.env 的 ADMIN_USERNAME / ADMIN_PASSWORD
sudo deploy/scripts/healthcheck.sh
sudo deploy/scripts/backup.sh
```

约定：密钥只出现在 `/etc/agent-platform/secrets.env`（600），仓库与配置模板里不落密钥。
