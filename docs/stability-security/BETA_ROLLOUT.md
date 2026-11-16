# Beta 发布与回滚（仅文档）

本说明只描述发布前检查与渐进放量，不执行实际发布。

## 发布前备份

在切换到含本修复的版本前，备份：

1. 平台 SQLite：`PLATFORM_DATA_DIR/platform.sqlite` 与同目录加密密钥；
2. 各会话 Checkpoint：`*/checkpoint.sqlite`（及 `-wal`/`-shm`）；
3. Workspace / 文件库目录；
4. 后端数据库与 Redis 会话（如适用）；
5. 当前运行镜像/配置快照，保留基线提交 `58d3cee39a27c95223760666993af6595ff61161` 的可回滚产物。

## 证书登录边界验收（必须）

- Spring Boot 仅监听可信地址（生产默认 `127.0.0.1:8080`，或内部网卡 + 防火墙）。
- Nginx 在全部转发路径上使用 `proxy_set_header` **覆盖** `X-Client-Verify` / `X-Client-DN` / `X-Client-Cert`，禁止透传客户端同名 Header。
- 仅当边界确认后设置 `CERT_LOGIN_ENABLED=true`，并配置 `CERT_LOGIN_TRUSTED_PROXIES`。
- 无法确保代理边界时，保持 `CERT_LOGIN_ENABLED=false`（默认），伪造 Header 不得获得身份。

## 个人模型 SSRF

- 可选：`PERSONAL_MODEL_ALLOWED_HOSTS=api.example.com,other.example.com`
- 未配置白名单时仍拒绝回环/私网/链路本地等地址，且仅允许 HTTPS。

## 网关超时

| 配置 | 默认 | 用途 |
| --- | --- | --- |
| `agent.runtime.connect-timeout-ms` | 5000 | 连接 |
| `agent.runtime.read-timeout-ms` | 60000 | 普通 REST |
| `agent.runtime.sse-read-timeout-ms` | 0 | SSE 长连接 |
| `agent.runtime.file-read-timeout-ms` | 300000 | 文件传输 |

## 渐进放量

1. 测试账号验证：普通对话、进程重启后 checkpoint 续聊、审批恢复、后台任务 interrupted、文件交付；
2. 确认伪造证书 Header 无身份、非法个人 API 被拒绝；
3. 再渐进放量，**不超过 10 人**；
4. 出现异常则整体回滚到基线镜像与备份数据。

## 明确不做

自动重试失败 Agent/工具、跨节点恢复、分布式队列、多进程调度、SSE 架构重写、前端重设计。
