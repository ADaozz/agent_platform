# 测试证据（本 PR）

基线 SHA：`58d3cee39a27c95223760666993af6595ff61161`

## 已执行

| 命令 | 结果 |
| --- | --- |
| `cd agent-runtime && .venv/bin/python -m pytest -q tests/test_runtime.py tests/test_platform.py tests/test_isolation.py tests/test_personal_models.py tests/test_stability_baseline.py tests/test_url_safety.py tests/test_platform_recovery.py tests/test_process_recovery_integration.py tests/test_capabilities.py tests/test_features.py` | **98 passed** |
| `cd agent-runtime && node --test tests/*.test.mjs` | **36 passed** |
| `cd backend && JAVA_HOME=.../java-17-openjdk-amd64 mvn -Dtest=CertTrustedProxyTest,AgentRuntimeTimeoutTest,LogDesensitizeUtilsTest test` | **17 passed** |

## 审查后续（仍为 draft）

- `CertLoginRedirectTest`：回跳不使用 Host；未配置 public origin 时失败；启用证书登录必须同时有可信代理与 HTTPS Origin。
- `test_kill_after_file_write_does_not_replay_tool`：真实进程在 `write_file` 之后被 SIGKILL，重启后续聊标记文件仍为 `marker-once`。
- `test_kill_while_waiting_for_approval_keeps_interrupt`：审批中 SIGKILL 后状态仍为 `waiting_confirmation`。
- `test_delete_keeps_store_when_runner_close_times_out`：`close()` 失败返回 409，Store 与 Checkpoint 保留。
- 构建失败且首次 `close()` 超时后，Runner 进入待清理，不会交给后续 `invoke()`。流结束后再次 `close()` 成功，会话可以重建并继续。
- 写文件崩溃测试改为追加计数：重启后续聊标记仍为单个 `x`，重复执行会变成 `xx`。
- 后台记录脱敏改为与子代理日志相同的已知密钥替换。
- 真实 Nginx + 浏览器 + sign.p12 的证书登录尚未在本环境执行，因此 PR 保持 Draft。

## 恢复相关验收要点

- `test_build_reloads_session_like_cli_switch_and_arms_recovery`：`Runtime.build()` 经 `switch_session` 装载 RecoveryContext；checkpoint 可读；续聊后上下文清除；用户 transcript 不被恢复提示污染。
- `test_recovery_middleware_is_one_shot_and_keeps_user_text_raw`：恢复说明只注入一次。
- `test_waiting_confirmation_keeps_interrupt_and_skips_recovery`：审批中断与 Platform 状态对齐。
- `test_uvicorn_restart_preserves_checkpoint_and_marks_interrupted`：真实 uvicorn 进程 kill/restart 后会话为 `interrupted`。
- 后台任务：重启后 `running → interrupted`，已完成结果保留；运行中删除返回 409。

## 环境说明 / 缺口

- 本 Cloud Agent 环境最初无 `bwrap` / `python3-venv` / JDK17；已在会话内安装后跑通上述命令。
- `BackendApplicationTests`（全量 Spring 上下文）依赖 Redis/DB，本轮未宣称通过。
- 前端 `npm run test:e2e:office` 未在本轮执行（需完整前端构建与浏览器环境）。
- 证书伪造 Header 的身份拒绝以 `CertTrustedProxyTest` 单元证据为准；完整 mTLS Nginx 路径需在部署机验收。

## 结论

核心 P0/P1 修复相关自动化已通过；**不能仅凭本环境宣称可合并到生产**，需在目标部署完成证书代理边界与 Beta 备份验收。
