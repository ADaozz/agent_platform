# personalDemo Backend 开发文档

> 本文档面向后端开发者，详细说明各模块的功能实现方式、核心类职责、数据流转与业务规则。  
> 前端对接见 [API.md](./API.md)，项目骨架复用见 [SKELETON.md](./SKELETON.md)，解耦与依赖总览见 [DDD-DECOUPLING.md](./DDD-DECOUPLING.md)。

---

## 目录

- [1. 项目概览](#1-项目概览)
- [2. 整体架构](#2-整体架构)
- [3. 启动与配置模块](#3-启动与配置模块)
- [4. 公共基础设施（common）](#4-公共基础设施common)
- [5. 安全模块（security + config）](#5-安全模块security--config)
- [6. 认证模块（auth）](#6-认证模块auth)
- [7. 用户管理（system/user）](#7-用户管理systemuser)
- [8. 角色管理（system/role）](#8-角色管理systemrole)
- [9. 权限管理（system/permission、system/menu）](#9-权限管理systempermissionsystemmenu)
- [10. 虚机管理（asset/host）](#10-虚机管理assethost)
- [11. 应用管理（asset/app）](#11-应用管理assetapp)
- [12. API Token（api）](#12-api-tokenapi)
- [13. 仪表盘统计（statistics）](#13-仪表盘统计statistics)
- [14. 定时任务（quartz）](#14-定时任务quartz)
- [15. 数据库设计](#15-数据库设计)
- [16. 开发约定与扩展指南](#16-开发约定与扩展指南)
- [17. 客户端证书与 mTLS 部署](#17-客户端证书与-mtls-部署)

---

## 1. 项目概览

### 1.1 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 语言 | Java | 1.8 |
| 框架 | Spring Boot | 2.6.13 |
| ORM | MyBatis-Plus | 3.5.5 |
| 数据库 | 人大金仓 KingbaseES | 8.6.0 |
| 缓存 | Redis + Spring Data Redis | 登录会话 / API Token |
| 认证 | Apache Shiro + JWT (jjwt) | 1.13.0 / 0.11.5 |
| 密码 | BCrypt (spring-security-crypto) | — |
| AOP | spring-boot-starter-aop | 操作日志 / 权限切面 |
| 调度 | spring-boot-starter-quartz | 定时任务 Cron 调度 |

### 1.2 模块完成度

| 模块 | 路径 | 状态 |
|------|------|------|
| 认证 | `auth/` | ✅ 已实现 |
| 安全 | `security/` + `config/ShiroConfig` | ✅ 已实现 |
| 用户管理 | `system/user/` | ✅ 已实现 |
| 角色管理 | `system/role/` | ✅ 已实现 |
| 权限管理 | `system/permission/` | ✅ 已实现（只读列表） |
| 菜单与授权树 | `system/menu/` | ✅ 已实现（只读，仅 admin） |
| 虚机 / 应用 | `asset/host/`、`asset/app/` | ✅ 已实现（P1：VmHost 聚合 + 读写分离） |
| 仪表盘 | `statistics/` | ✅ 已实现 |
| API Token | `api/` | ✅ 已实现 |
| 操作日志 | `common/aspect/LogAspect` + `common/operlog` | ✅ 控制台 + `sys_oper_log` 异步落库 |
| 定时任务 | `quartz/` | ✅ 已实现 |
| 客户端证书 | `auth/cert/` | ✅ 已实现 |

### 1.3 包结构

```text
org.example.backend/
├── BackendApplication.java       # 启动类
├── config/                         # Shiro、MyBatis-Plus、Quartz 配置
├── auth/                           # 登录、当前用户信息
│   ├── cert/                       # 客户端证书申请/签发/登录
│   └── session/                    # 登录设备会话
├── security/                       # JWT 过滤器、Realm、权限切面
├── system/
│   ├── user/                       # 用户 CRUD、角色分配
│   ├── role/                       # 角色 CRUD、权限绑定
│   └── permission/                 # 权限列表查询
├── asset/
│   ├── host/                       # 虚机（含 domain / application / infrastructure）
│   ├── app/                        # 应用（写路径经 VmHostRepository）
│   ├── port/                       # UserQueryPort（跨上下文读 IAM）
│   ├── infrastructure/acl/         # UserQueryAdapter
│   └── constant/                   # VmLifecycleStatus（@Deprecated，委托 VmLifecycle）
├── api/                            # API Token (AK/SK)
├── statistics/                     # 仪表盘聚合
├── quartz/                         # 定时任务（扫描注册 + Quartz 调度）
└── common/                         # 公共工具、异常、VO、切面
```

每个业务模块默认遵循统一分层：

```text
模块/
├── controller/     # REST 接口，@RequiresPermissions、@Log、@Valid
├── service/        # 接口 + impl，业务逻辑
├── mapper/         # MyBatis-Plus BaseMapper + 自定义 @Select
├── entity/         # @TableName 数据库实体
├── dto/            # 入参（Query / Create / Update）
└── vo/             # 出参
```

**Asset 模块（P1 聚合试点）** 在写路径上额外拆分：

```text
asset/host/
├── domain/model/           # VmHost 聚合根、VmLifecycle 值对象
├── domain/repository/      # VmHostRepository 接口
├── application/            # VmHostApplicationService（写）、VmHostQueryService（读）
├── infrastructure/persistence/  # VmHostRepositoryImpl、VmHostConverter
├── service/impl/           # VmHostServiceImpl（门面，委托 Application）
└── controller/ … entity/ mapper/ dto/ vo/

asset/app/
├── application/            # VmAppApplicationService（写，经 VmHostRepository 校验）
└── service/impl/           # VmAppServiceImpl（门面 + 列表查询）
```

跨上下文查用户名：`UserQueryPort` ← `UserQueryAdapter` → `SysUserService`（防腐层，见 [DDD-DECOUPLING.md §4.1](./DDD-DECOUPLING.md#41-依赖关系总览改后)）。

---

## 2. 整体架构

### 2.1 请求处理链路

```text
HTTP 请求
    │
    ▼
Shiro Filter 链 (/login=anon, /**=jwt)
    │
    ▼
JwtFilter
    ├── /login → 放行
    ├── X-Access-Key + X-Secret-Key → ApiAuthToken
    ├── Authorization: Bearer xxx → JwtToken
    └── 无凭证 → 401 JSON
    │
    ▼
UserRealm.doGetAuthenticationInfo
    ├── JwtToken → 验签，principal = userId
    └── ApiAuthToken → 验签 + 查库，principal = userId
    │
    ▼
Controller 方法
    ├── PermissionAspect → @RequiresPermissions 校验
    ├── LogAspect → 操作日志（控制台 + sys_oper_log）
    └── Service → 业务逻辑（Asset 写路径：ApplicationService → 聚合/Repository）→ Mapper → DB
    │
    ▼
AjaxResult { code, msg, data }
    │
    ▼
GlobalExceptionHandler（BusinessException / 403 / 校验异常）
```

### 2.2 认证 vs 授权

| 层级 | 机制 | 问题 |
|------|------|------|
| **认证** | JwtFilter + UserRealm | 你是谁？Token 有效吗？ |
| **授权** | @RequiresPermissions + PermissionAspect | 你能调这个接口吗？ |
| **业务级授权** | Domain / Application 内 assert（如 `VmHost.assertOwnedBy`） | 你能改这条数据吗？ |

### 2.3 统一响应格式

所有 Controller 返回 `AjaxResult`：

```json
{
  "code": 0,       // 0=成功，500=失败
  "msg": "操作成功",
  "data": { ... }
}
```

分页列表统一包装为 `PageResultVO`：

```json
{
  "total": 100,
  "rows": [ ... ]
}
```

系统表关联字段（角色、权限、owner）统一用 `OptionVO`：

```json
{ "id": 1, "label": "admin" }
```

---

## 3. 启动与配置模块

### 3.1 BackendApplication

**文件：** `BackendApplication.java`

**职责：**

- `@SpringBootApplication` 启动 Spring Boot
- `@EnableAspectJAutoProxy(proxyTargetClass = true)` — **必须**，使 PermissionAspect 和 LogAspect 对 Controller 生效（CGLIB 代理）
- `@MapperScan` 扫描所有 Mapper 包

**Mapper 扫描包列表：**

```java
"org.example.backend.system.user.mapper"
"org.example.backend.system.role.mapper"
"org.example.backend.system.permission.mapper"
"org.example.backend.system.menu.mapper"
"org.example.backend.asset.host.mapper"
"org.example.backend.asset.app.mapper"
"org.example.backend.api.mapper"
"org.example.backend.quartz.mapper"
"org.example.backend.statistics.mapper"
```

新增业务模块时，必须在此处追加 Mapper 包路径。

### 3.2 application.yml 与环境 Profile

**配置文件：**

| 文件 | 作用 |
|------|------|
| `application.yml` | 公共配置（数据源、JWT、MyBatis-Plus） |
| `application-dev.yml` | 本地开发：`server.port: 8081` |
| `application-prod.yml` | 生产部署：`server.port: 8080` |

**端口切换：**

| 场景 | 激活 Profile | 端口 |
|------|--------------|------|
| IntelliJ 运行 `BackendApplication` | `dev`（已在 `.idea/runConfigurations` 配置） | **8081** |
| `java -jar` / systemd 未指定 profile | 无（Spring Boot 默认） | **8080** |
| 显式生产 | `prod` | **8080** |

生产 systemd 建议在 `ExecStart` 增加环境变量：

```ini
Environment=SPRING_PROFILES_ACTIVE=prod
```

**关键配置项（application.yml）：**

| 配置 | 说明 |
|------|------|
| `spring.datasource.*` | KingbaseES 连接（驱动 `com.kingbase8.Driver`） |
| `spring.redis.*` | Redis 地址、端口、密码与数据库编号；默认 `127.0.0.1:6379/0` |
| `mybatis-plus.global-config.db-config.schema: public` | 避免 `sys_user` 与 Kingbase 系统视图同名冲突 |
| `jwt.secret` | 登录 JWT 签名密钥（HS256，≥32 字符） |
| `jwt.expire` | 登录 Token 过期秒数（默认 7200 = 2 小时） |
| `jwt.api.secret` | API Token SK 签名密钥（与登录 JWT 分离） |
| `jwt.api.expire` | API Token 过期秒数（默认 604800 = 7 天） |

### 3.3 MybatisPlusConfig

**文件：** `config/MybatisPlusConfig.java`

**实现：**

- 注册 `MybatisPlusInterceptor`
- 添加 `PaginationInnerInterceptor(DbType.POSTGRE_SQL)` — Kingbase 使用 PostgreSQL 方言分页

**效果：** Service 中 `page(new Page<>(pageNum, pageSize), wrapper)` 自动追加 `LIMIT/OFFSET`。

### 3.4 ShiroConfig

**文件：** `config/ShiroConfig.java`

**实现要点：**

1. **SecurityManager**
   - 绑定 `UserRealm`
   - 关闭 Session 存储（`setSessionStorageEnabled(false)`）— 无状态 JWT 模式

2. **JwtFilter**
   - 注册为名为 `jwt` 的自定义 Filter

3. **过滤器链**
   ```java
   chain.put("/login", "anon");   // 登录匿名访问
   chain.put("/**", "jwt");       // 其余全部走 JWT 认证
   ```
   - **不在 Filter 链配置 `perms[xxx]`**，接口级权限由 Controller 注解 + Aspect 处理

### 3.5 QuartzConfig

**文件：** `config/QuartzConfig.java`、`config/AutowiringSpringBeanJobFactory.java`

**职责：**

1. 注册 `AutowiringSpringBeanJobFactory`，使 Quartz 创建的 `QuartzJob` 实例支持 Spring 依赖注入
2. 通过 `SchedulerFactoryBeanCustomizer` 将 JobFactory 绑定到 Spring Boot 自动配置的 Scheduler

**任务扫描：** 启动时 `TaskRegistry`（`@PostConstruct`）扫描 Spring 容器中所有 `Task` Bean，将带 `@TaskInfo` 且 `sys_job` 中尚不存在的任务 **insert** 入库（Cron 为空、`enabled=0`），并输出扫描日志。

**调度加载：** 应用上下文就绪后，`QuartzJobLoader` 从 **`sys_job` 表** 查询 `enabled=1` 的记录，将 Cron、beanName 等写入 Quartz Scheduler。业务配置的权威来源是数据库，不是内存里的硬编码。

**两层存储说明：**

| 层级 | 存储 | 作用 |
|------|------|------|
| 业务表 | `sys_job` | Cron、启用状态、beanName；启动与用户修改均读写此表 |
| 代码扫描 | `TaskRegistry` | 仅首次发现新 Task 类时 **insert** 到 `sys_job`，不做调度 |
| Quartz 运行时 | 内存 JobStore | 启动后按 `sys_job` 重建调度；重启后会再次从 DB 加载 |

**启动日志（正常 INFO，非报错）：**

```text
TaskRegistry      : 扫描 Task Bean 完成：共 2 个，带 @TaskInfo 2 个，新写入 sys_job 0 个
QuartzJobLoader   : 从 sys_job 加载已启用的定时任务到 Quartz Scheduler...
QuartzSchedulerService : 从 sys_job 加载已启用任务，共 0 条
```

| 日志字段 | 含义 |
|----------|------|
| 共 X 个 | 容器中 `Task` 类型 Bean 总数 |
| 带 @TaskInfo Y 个 | 会被注册到 `sys_job` 的任务数（无注解的 Task 跳过） |
| 新写入 sys_job Z 个 | 本次启动新插入的记录数（已存在则跳过） |
| 已启用任务共 N 条 | 仅统计 `enabled=1`；为 0 表示有任务但未启用，或表中尚无任务 |

Quartz 初始化时可能短暂出现 `NOT STARTED` / `standby mode`，属调度器创建过程中的状态快照；Spring Boot 完成启动后会 `start()` 调度器。

---

## 4. 公共基础设施（common）

### 4.1 AjaxResult / ResultCode

**文件：** `common/result/AjaxResult.java`

- 继承 `HashMap<String, Object>`
- `success(msg, data)` → code=0
- `error(msg, data)` → code=500

### 4.2 BusinessException

**文件：** `common/exception/BusinessException.java`

- 携带 `Module.ModuleType`（AUTH / SYSTEM / ASSET / API / STATISTICS）
- Service 层业务失败统一抛出，由 `GlobalExceptionHandler` 捕获
- 返回格式：`"{模块名}错误:{message}"`

**Module 枚举：**

| 值 | 含义 |
|----|------|
| AUTH | 认证相关 |
| SYSTEM | 用户/角色/权限 |
| ASSET | 虚机/应用 |
| API | API Token |
| STATISTICS | 仪表盘 |

### 4.3 GlobalExceptionHandler

**文件：** `common/exception/GlobalExceptionHandler.java`

| 异常类型 | HTTP 状态 | 返回 msg |
|----------|-----------|----------|
| `BusinessException` | 200（body code=500） | `{模块}错误:{message}` |
| `AuthorizationException` | **403** | `无权限访问` |
| `MethodArgumentNotValidException` | 200 | 字段校验消息拼接 |
| `BindException` | 200 | 同上 |
| `ConstraintViolationException` | 200 | 同上 |
| `Exception` | 200 | `全局错误:{message}` |

> 注意：401 由 JwtFilter 直接写 HTTP 响应，不经过 GlobalExceptionHandler。

### 4.4 JwtUtils（登录 Token）

**文件：** `common/utils/JwtUtils.java`

**签发（createToken）：**

```text
输入：userId, userName, sessionId（登录会话 jti）
Claims：
  - jti / id = sessionId
  - sub = userName
  - userId = 数据库 userId
  - iat / exp
算法：HS256，密钥 jwt.secret
```

**验签（parseToken）：**

- 使用 `Jwts.parserBuilder().setSigningKey(...).parseClaimsJws(token)`
- 过期或签名错误抛异常，UserRealm 转为 `AuthenticationException`
- 验签通过后 `LoginSessionService.assertSessionActive(jti)` 校验会话未踢出

**辅助方法：**

- `getUsername(claims)` → subject
- `getUserId(claims)` → claim "userId"
- `getJti(claims)` → jti / id
- `extractBearerToken(request)` → Authorization Bearer 值

### 4.5 ApiJwtUtils（API Token SK）

**文件：** `common/utils/ApiJwtUtils.java`

与登录 JWT **使用不同密钥**（`jwt.api.secret`）和过期时间（`jwt.api.expire`）。

**AK 生成：**

```java
"ak-" + UUID.randomUUID().toString().replace("-", "")
```

**SK 签发（createSecretKey）：**

```text
Claims：
  - sub = accessKey
  - type = "api"
  - accessKey = AK
  - userId = 所属用户
  - asset = ["vm", "app"] 等授权资源列表
  - iat / exp
```

**验签后辅助方法：**

- `isApiToken(claims)` → type == "api"
- `getAccessKey(claims)` / `getUserId(claims)` / `getAssets(claims)`

### 4.6 PasswordUtils

**文件：** `common/utils/PasswordUtils.java`

- 使用 `BCryptPasswordEncoder`（spring-security-crypto，不引入完整 Spring Security）
- `encrypt(password)` → BCrypt 哈希，用于创建/修改用户
- `matches(raw, encoded)` → 登录密码比对

### 4.7 Log 注解 + LogAspect

**文件：** `common/annotation/Log.java`、`common/aspect/LogAspect.java`

**@Log 属性：**

| 属性 | 说明 |
|------|------|
| title | 模块名，如「用户管理」 |
| businessType | INSERT / UPDATE / DELETE / QUERY / GRANT / OTHER |
| operatorType | MANAGE / OTHER |
| isSaveRequestData | 是否记录请求参数（默认 true） |
| isSaveResponseData | 是否记录响应（默认 true） |
| excludeParamNames | 排除字段（大小写不敏感，匹配到的字段**不会写入**日志），如 `passWord` |
| sensitiveParamNames | 额外全掩码字段（大小写不敏感，与全局规则合并） |

**脱敏规则（`LogDesensitizeUtils`，写入控制台与 `sys_oper_log` 前统一处理）：**

| 类型 | 字段名（大小写不敏感） | 规则 |
|------|------------------------|------|
| 全掩码 | `passWord`、`password`、`p12Password`、`secretKey`、`secret`、`privateKey`、`credential` 等 | 替换为 `******` |
| 部分掩码 | `token`、`accessToken`、`refreshToken`、`authorization`、`sessionId` | 长度 ≤ 8 → `******`；否则 `前4 + **** + 后4` |

- `excludeParamNames` **优先于掩码**：匹配到的 key 直接从 JSON 中删除
- `sensitiveParamNames` 可补充接口级全掩码字段
- 嵌套对象、数组、`AjaxResult.data` 均递归处理

**LogAspect 实现：**

- `@Around("@annotation(controllerLog)")` 环绕通知，`@Order(100)`
- 记录：模块、类型、操作人 userId、方法名、耗时、状态、请求/响应 JSON（经 `LogDesensitizeUtils` 脱敏）
- **控制台摘要** + **`SysOperLogService.saveAsync`** 写入 `sys_oper_log`（需执行 `22-oper-log.sql`）
- 过滤 HttpServletRequest/Response、MultipartFile、BindingResult；文本字段截断 2000 字符

**相关文件：** `common/utils/LogDesensitizeUtils.java`、`common/operlog/`、`config/AsyncConfig.java`、`resources/sql/22-oper-log.sql`

### 4.8 公共 VO

| 类 | 字段 | 用途 |
|----|------|------|
| `PageResultVO<T>` | total, rows | 分页列表 |
| `OptionVO` | id, label | 角色/权限/owner 下拉选项 |

---

## 5. 安全模块（security + config）

### 5.1 JwtToken

**文件：** `security/token/JwtToken.java`

Shiro 的 `AuthenticationToken` 包装类：

- principal = credentials = JWT 字符串
- UserRealm 从 credentials 解析验签

### 5.2 ApiAuthToken

**文件：** `security/token/ApiAuthToken.java`

- principal = accessKey
- credentials = secretKey（JWT 格式 SK）

### 5.3 JwtFilter

**文件：** `security/filter/JwtFilter.java`

继承 Shiro `AuthenticatingFilter`，核心方法：

#### isAccessAllowed

```text
1. servletPath == "/login" → true（放行）
2. 请求含 X-Access-Key 或 X-Secret-Key → false（走 onAccessDenied 认证）
3. Subject 已 authenticated → true
4. 否则 → false
```

#### createToken

按优先级解析凭证：

1. **AK/SK 模式：** 请求头 `X-Access-Key` + `X-Secret-Key`（必须同时存在）→ `ApiAuthToken`
2. **Bearer 模式：** `Authorization: Bearer <token>` → `JwtToken`
3. 格式不对或缺失 → null

#### onAccessDenied

```text
1. OPTIONS 预检 → 放行（CORS）
2. AK/SK + 非 GET → 403 "API Token 只允许 GET 查询"
3. AK/SK + 路径非 /asset/vm 或 /asset/app → 403 "API Token 未授权访问该业务资源"
   （通过 ApiJwtUtils 解析 SK 中的 asset claim 与路径匹配）
4. createToken == null → 401 "未登录或 token 缺失"
5. executeLogin → UserRealm 验签
6. 验签失败 → onLoginFailure → 401 "token 无效或已过期"
```

#### hasAssetPermission

AK/SK 访问时的资源授权校验：

```text
1. 解析 X-Secret-Key JWT
2. 验证 type=api 且 accessKey 匹配
3. 根据 servletPath 推断 asset（/asset/vm → "vm"，/asset/app → "app"）
4. 检查 claims.asset 列表是否包含该 asset
```

### 5.4 UserRealm

**文件：** `security/realm/UserRealm.java`

#### supports

```java
token instanceof JwtToken || token instanceof ApiAuthToken
```

#### doGetAuthenticationInfo — JWT 路径

```text
1. jwtUtils.parseToken(tokenStr) → userId、jti
2. loginSessionService.assertSessionActive(jti)   # Redis 会话仍有效
3. sysUserService.assertUserActive(userId)        # DB status == 正常
4. return SimpleAuthenticationInfo(userId, tokenStr, realmName)
   → principal 存 userId（Long），后续 LoginUserUtils 使用
```

#### doGetAuthenticationInfo — AK/SK 路径

```text
1. apiJwtUtils.parseToken(secretKey)
2. 验证 type=api、accessKey 匹配
3. apiTokenService.assertTokenActive(ak, sk, userId)  # Redis 优先，未命中回源 DB
4. sysUserService.assertUserActive(userId)            # DB status == 正常
5. return SimpleAuthenticationInfo(userId, secretKey, realmName)
```

> AK/SK 认证成功后，Subject 的 principal 同样是 userId，与 JWT 登录一致。

#### doGetAuthorizationInfo

```text
1. 从 principals 取 userId
2. sysRoleService.selectSysRoleByUserId(userId) → setRoles
3. sysPermissionService.selectSysPermissionByUserId(userId) → setStringPermissions
```

权限数据由 `doGetAuthorizationInfo` 从 DB 加载，Shiro 按 userId 缓存；**RBAC 写操作后**通过 `AuthorizationCacheEvictor` 失效缓存，同 token 下次请求即生效。

### 5.5 PermissionAspect

**文件：** `security/aspect/PermissionAspect.java`

**为什么需要：** Shiro 自带 `@RequiresPermissions` Advisor 与 Spring Boot AOP 并存时可能不生效。

**实现：**

```java
@Before("@annotation(requiresPermissions)")
public void checkPermission(RequiresPermissions requiresPermissions) {
    Subject subject = SecurityUtils.getSubject();
    if (logical == OR) → anyMatch isPermitted
    else → checkPermissions(perms)  // AND，缺一则抛 AuthorizationException
}
```

`@Order(0)` 确保权限校验优先于 LogAspect。

### 5.6 AuthorizationCacheEvictor

**文件：** `security/cache/AuthorizationCacheEvictor.java`

**触发点：**

| 操作 | 方法 |
|------|------|
| 用户分配角色 | `SysUserServiceImpl.assignUserRoles` → `evictByUserId` |
| 用户停用 / 删除 | `UserStatusChangedAuthCacheListener` → `evictByUserId`（事件驱动，见 §7.3） |
| 角色分配权限 | `SysRoleServiceImpl.assignPermissionsForRole` → `evictByRoleId` |
| 删除角色 | `SysRoleServiceImpl.deleteRole` → `evictByRoleId` |

**ShiroConfig：** `MemoryConstrainedCacheManager` + `userRealm.setAuthorizationCachingEnabled(true)`。

### 5.7 LoginUserUtils

**文件：** `security/context/LoginUserUtils.java`

```java
public static Long getUserId() {
    Object principal = SecurityUtils.getSubject().getPrincipal();
    return principal == null ? null : (Long) principal;
}
```

全项目获取当前登录用户 ID 的统一入口。

---

## 6. 认证模块（auth）

### 6.1 接口一览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/login` | 匿名 | 用户名密码登录，创建会话并签发含 jti 的 JWT |
| POST | `/login/cert` | 匿名 | 客户端证书登录（Nginx mTLS 头解析） |
| POST | `/logout` | 登录即可 | 吊销当前会话 |
| GET | `/user/info` | 登录即可 | 当前用户角色/权限 |
| GET | `/system/session` | system:session:list | 登录设备列表（manage 可查全部用户） |
| DELETE | `/system/session/{sessionId}` | system:session:kick | 踢出指定设备 |

### 6.2 AuthController

**文件：** `auth/controller/AuthController.java`

- `POST /login`：`@Valid LoginDTO`，记录 IP/User-Agent，admin 先吊销旧会话
- `POST /logout`：从 JWT 解析 jti，删除 Redis 当前会话并更新 DB 下线历史
- `GET /user/info`：不记录响应体（`isSaveResponseData = false`）

### 6.3 AuthServiceImpl — 登录流程

**文件：** `auth/service/impl/AuthServiceImpl.java`

```text
login(LoginDTO, HttpServletRequest):
  1. 校验用户名密码
  2. issueLoginSuccess(userId, userName, request, loginType=0)

loginByCert(HttpServletRequest):
  1. CertLoginService 解析 X-Client-Cert，匹配 sign 证指纹
  2. issueLoginSuccess(userId, userName, request, loginType=1)

issueLoginSuccess(...):
1. loginSessionService.createSingleLoginSession(userId, ip, userAgent, loginType) → sessionId
  2. sysUserService.updateLastLoginTime(userId)
  3. jwtUtils.createToken(userId, userName, sessionId) → token
  4. buildUserInfo(userId) → SysUserInfoVO
  5. 封装 LoginVO { token, sessionId, user }
```

```text
logout(HttpServletRequest):
  1. 从 Authorization 解析 JWT jti
  2. loginSessionService.revokeSession(jti)
  3. 删除 personal-demo:session:{jti}
  4. 若 jti 仍是该用户当前会话，删除 personal-demo:user-active-session:{userId}
  5. sys_login_session.status=1，记录 revoke_time
```

```text
getCurrentUser():
  1. LoginUserUtils.getUserId()
  2. sysUserService.getCurrentUserInfo(userId)
     → 含 roles (OptionVO[]) 和 permissions (OptionVO[])
```

### 6.4 登录设备会话（auth/session）

**表：** `sys_login_session`（session_id = JWT jti）

| 策略 | 说明 |
|------|------|
| 全用户 | **单点登录**：新登录前 `createSingleLoginSession` 吊销全部 active 会话 |
| 设备列表 | 按 userId 聚合为一行；`GET /system/session/history` 查完整登录轨迹 |
| 在线判断 | Redis `personal-demo:session:{sessionId}` 是实时依据；列表用 `multiGet` 批量校准 DB 中的 active 记录 |
| 踢出 | 普通用户可踢自己的其他设备；manage 可踢任意用户 |
| 管理员 | `system:session:manage` 可查看/踢出任意用户的设备 |

**Redis Key：**

```text
personal-demo:session:{sessionId}          -> userId，TTL = jwt.expire
personal-demo:user-active-session:{userId} -> sessionId，TTL = jwt.expire
```

**踢出效果：** 删除 Redis session + DB `status=1` → 下次请求 UserRealm 拒绝 → 401。Redis TTL 自然到期不会自动更新历史表，因此设备列表展示前以 `multiGet` 结果覆盖实时状态，但不修改数据库记录。

### 6.5 数据结构

**LoginDTO：** `{ userName, passWord }` — passWord 带 `@NotBlank`

**LoginVO：** `{ token, sessionId, user: SysUserInfoVO }`

**SysUserInfoVO：** `{ userId, username, roles: OptionVO[], permissions: OptionVO[] }`

### 6.6 客户端证书（auth/cert）

**包路径：** `auth/cert/`

| 类 | 职责 |
|----|------|
| `CertLoginServiceImpl` | 读 Nginx 头，仅接受 `X-Client-Verify=SUCCESS`，再按 `X-Client-Cert` SHA-256 指纹查库 |
| `CertIssueServiceImpl` | BouncyCastle 签发 sign + encrypt 双证，生成 p12 与 bundle.zip（**README 不含 P12 密码**） |
| `CertApplyServiceImpl` | 申请/重发/审批/拒绝/吊销/下载；`revealP12Password` 用 `LambdaUpdateWrapper` 一次性返回并清库 |
| `UserCertController` | `/system/cert/mine/*` |
| `CertManageController` | `/system/cert/*` 管理端 |

**表：**

- `sys_cert_apply` — 申请单（`pending` / `approved` / `rejected`）
- `sys_user_cert` — 已签发证书（`sign` / `encrypt`；登录仅匹配 sign）

**配置（`application.yml` → `cert.*`）：**

```yaml
cert:
  storage-base-path: /home/neo/application/personalDemo/ca/client/users
  intermediate-cert: .../ca/intermediate/intermediate-ca.crt
  intermediate-key: .../ca/intermediate/intermediate-ca.key
  root-cert: .../ca/root/root-ca.crt   # 仅公钥，打入用户 bundle.zip
  default-valid-days: 365
  p12-password-length: 16
```

**Shiro anon：** `/login/cert`、`/login/cert/check`、`/login/cert/debug`；其余证书 API 走 JWT + `@RequiresPermissions`。

**登录入口：** 浏览器整页跳转 `https://{host}:8443/login/cert?redirect=1`（非 443 `/api/login/cert`）。

**P12 密码：**

- 签发时随机生成，审批响应中一次性返回给管理员（管理员弹窗关闭后前端不再保留，**不能**从列表接口再次获取）
- 写入 `sys_cert_apply.p12_password`，用户通过 `POST /system/cert/mine/reveal-password/{applyId}` 领取一次
- 领取后须用 `LambdaUpdateWrapper.set(p12Password, null)` 清库；`updateById` 无法将字段更新为 NULL（MyBatis-Plus 默认 `NOT_NULL` 策略）
- `revealP12Password` 更新条件含 `isNotNull(p12Password)`，避免并发重复领取
- `bundle.zip` / `README.txt` **不包含**密码；列表 VO 仅 `p12PasswordPending`
- 前端 `MyCertView`：领取成功后写入会话级 `consumedPasswordApplyIds`，与后端清库双保险

---

## 7. 用户管理（system/user）

### 7.1 接口一览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/system/user` | system:user:list | 分页/详情/按角色筛选 |
| POST | `/system/user` | system:user:add | 新增用户 |
| PUT | `/system/user` | system:user:edit | 修改用户 |
| PUT | `/system/user/authRole` | system:user:edit | 分配角色 |
| DELETE | `/system/user/{userId}` | system:user:delete | 删除用户 |

### 7.2 数据库表

**sys_user：**

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | BIGINT PK | 用户 ID |
| user_name | VARCHAR(64) UNIQUE | 登录名 |
| pass_word | VARCHAR(128) | BCrypt 哈希 |
| status | CHAR(1) | 0=正常 |
| create_time / update_time / last_login_time | TIMESTAMP | |

**sys_user_role：** `(user_id, role_id)` 复合主键

### 7.3 SysUserServiceImpl 核心逻辑

#### createUser

```text
1. 用户名唯一性检查
2. BCrypt 加密密码
3. insert sys_user（status 默认 "0"）
4. sysUserRoleService.assignRolesByUserId(userId, roleIds)
   → 先删旧关联，再批量插入
```

#### updateUser

```text
1. 用户存在性检查
2. 用户名唯一性（排除自身）
3. 可选更新 status、passWord（非空则重新 BCrypt）
4. updateById
5. 若 status 从 0→1（正常→停用）：
   publish UserStatusChangedEvent(DISABLED)
   → AFTER_COMMIT：Session / ApiToken / Cert / AuthCache Listener 级联吊销
```

#### deleteUser

```text
1. 用户存在性检查
2. 不能删除当前登录用户
3. assertNotLastAdmin — 不能删除最后一个 admin 角色用户
4. 删除 sys_user_role 关联
5. 删除 sys_user
6. publish UserStatusChangedEvent(DELETED)
   → AFTER_COMMIT：同上 Listener 级联吊销（清理残留会话、Token、证书）
```

> **说明：** IAM 不再直接注入 `LoginSessionService` / `ApiTokenService` / `CertIssueService`；`SysUserServiceImpl` 仅发布 `UserStatusChangedEvent`（`system/user/event/`），各模块 `listener/` 包订阅处理。访问控制兜底仍为 `UserRealm.assertUserActive` 与登录时 `AuthServiceImpl` 的 status 校验。

#### assignUserRoles

```text
1. 用户存在性检查
2. assertNotRemoveLastAdminRole — 不能把最后一个 admin 用户的 admin 角色移除
3. assignRolesByUserId（全量替换）
```

#### listUserInfo

```text
QueryDTO 支持：
  - userId → 单条详情（total=1）
  - roleId → 先查 sys_user_role 得 userIds，再 in 查询
  - userName → like
  - status → eq
  - pageNum / pageSize → 分页

每条记录 toSysUserVO：
  - 基本信息 + roles (OptionVO[])
```

#### getCurrentUserInfo

供 `/user/info` 和登录返回使用，组装 roles + permissions 的 OptionVO 列表。

### 7.4 SysUserRoleServiceImpl

**assignRolesByUserId 模式（角色/权限分配通用）：**

```text
1. DELETE 该 userId 的全部 sys_user_role
2. 若 roleIds 非空，批量 INSERT 新关联
```

---

## 8. 角色管理（system/role）

### 8.1 接口一览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/system/role` | system:role:list | 分页/详情 |
| GET | `/system/role/options` | system:role:list | 全部角色下拉 |
| POST | `/system/role` | system:role:add | 新增角色 |
| PUT | `/system/role` | system:role:edit | 修改角色标识 |
| PUT | `/system/role/authPerm` | system:role:edit | 分配权限 |
| DELETE | `/system/role/{roleId}` | system:role:delete | 删除角色 |

### 8.2 数据库表

**sys_role：** `{ role_id, sys_role }` — sys_role 为角色标识（如 admin、user）

**sys_role_permission：** `(role_id, permission_id)` 复合主键

### 8.3 SysRoleServiceImpl 核心逻辑

#### assertAdmin

所有写操作和列表查询前调用：

```java
if (!SecurityUtils.getSubject().hasRole("admin")) {
    throw BusinessException(SYSTEM, "仅管理员可以操作角色和权限");
}
```

> 接口层有 `@RequiresPermissions`，Service 层额外校验 admin 角色，双重保障。

#### createRole

```text
1. assertAdmin
2. 角色标识唯一性
3. insert sys_role
4. assignPermissionsForRole(role, permissionIds)
```

#### updateRole

```text
1. assertAdmin
2. admin 角色的 sys_role 标识不可修改
3. 新标识唯一性（排除自身）
4. updateById
```

#### deleteRole

```text
1. assertAdmin
2. admin 角色不可删除
3. 若 sys_user_role 有绑定 → 拒绝删除
4. 删除 sys_role_permission 关联
5. 删除 sys_role
```

#### assignRolePermissions / assignPermissionsForRole

```text
1. assertAdmin
2. 若角色是 admin → 自动绑定全部 permission（忽略传入的 permissionIds）
3. 否则 → expandWithRequiredListPermissions（见下）→ 校验 permissionId 全部存在
4. sysRolePermissionService.assignPermissionsByRoleId（全量替换）
```

**list 基础权限自动补全（`expandWithRequiredListPermissions`）：**

接口级权限仍按 `add` / `edit` / `delete` / `list` 独立存储与鉴权；但在**角色分配写入**时，若勾选了同模块的 `add`、`edit` 或 `delete`，后端会自动补全对应的 `list` 权限，避免「有改无查、菜单不可见、列表接口 403」。

| 提交勾选 | 实际写入 |
|----------|----------|
| 仅 `system:user:list` | 仅 list |
| 仅 `system:user:edit` | edit + **list**（自动补全） |
| `system:user:edit` + `system:user:delete` | edit + delete + **list** |
| 仅 `dashboard:view:all` | 不变（非 add/edit/delete，不补 list） |

规则：权限标识以 `:add`、`:edit`、`:delete` 结尾时，查找同前缀的 `:list`（如 `monitor:job:edit` → `monitor:job:list`）；库中不存在对应 list 则跳过。

前端角色授权弹窗（`RoleListView.vue`）与之联动：

- 勾选 add/edit/delete → 同菜单分组内自动勾选 list
- 取消 list → 同分组内已勾选的 add/edit/delete 一并取消

> 前端的 `permissionIds` 统一由 `GET /system/menu/permTree`（见 9.4）勾选产生，新增走 `createRole`、编辑走 `assignRolePermissions`，两条写入路径不变，不需要为权限树新增写接口。

#### toRoleVO

```text
- roleId, sysRole
- permissions（OptionVO，label 为 perm_name 中文名，缺省回退权限标识）:
  - admin 角色 → 全部权限
  - 其他角色 → sys_role_permission 关联的权限
```

`listRoleInfo` 先用 `loadPermissionIndex()` 按 `permission_id` 升序把全部权限查一次建成 Map，再传给每行的 `toRoleVO`，避免逐个 `getByPermissionId` 的 N+1 查询，同时保证各角色的权限展示顺序一致。

### 8.4 SysRolePermissionServiceImpl

与 SysUserRoleServiceImpl 相同模式：

```text
assignPermissionsByRoleId(roleId, permissionIds):
  1. DELETE 该 roleId 的全部 sys_role_permission
  2. 批量 INSERT 新关联（distinct permissionIds）
```

### 8.5 SysRoleMapper 自定义 SQL

| 方法 | SQL 逻辑 |
|------|----------|
| selectSysRoleByUserId | user_role JOIN role，返回 sys_role 字符串列表 |
| selectRoleOptionsByUserId | 同上，返回 OptionVO(id=roleId, label=sysRole) |
| selectAllRoleOptions | 全表 role_id + sys_role |

> 所有 JOIN 使用 `public.sys_user_role`、`public.sys_role` 前缀，避免 Kingbase 系统视图冲突。

---

## 9. 权限管理（system/permission、system/menu）

### 9.1 接口一览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/system/permission` | system:role:list | 分页/详情 |
| GET | `/system/permission/options` | system:role:list | 全部权限下拉 |
| GET | `/system/menu/permTree` | system:role:list | 菜单+权限授权树（`system/menu` 模块，见 9.4） |

> 权限模块**不提供增删改**，权限字符串通过 SQL seed 脚本维护。

### 9.2 SysPermissionServiceImpl

#### listPermissionInfo / listAllPermissionOptions

```text
1. assertAdmin（hasRole("admin")）
2. 支持 permissionId 单条 / sysPermission like 模糊 / 分页
3. 返回 SysPermissionVO 或 OptionVO
```

#### selectSysPermissionByUserId

供 UserRealm 授权使用，SQL 路径：

```sql
sys_user_role → sys_role_permission → sys_permission
WHERE user_id = ?
→ DISTINCT sys_permission 字符串列表
```

### 9.3 权限字符串约定

格式：`{模块}:{资源}:{操作}`

| 权限 | 用途 |
|------|------|
| system:user:list/add/edit/delete | 用户 CRUD |
| system:role:list/add/edit/delete | 角色 CRUD |
| asset:vm:list | 虚机列表（seed 有，接口实际不校验） |
| asset:app:list | 应用列表（同上） |
| dashboard:view:all | 全局仪表盘 |
| api:token:list/add/get/delete | API Token 管理 |
| monitor:job:list/edit | 定时任务查询与修改 |

**菜单可见 vs 接口权限：**

- 系统管理类菜单（用户/角色/任务/API Token）在前端以 `*:list` 作为**页面入口**权限；无 list 则侧边栏与路由守卫均不可进入。
- 页面内按钮由 `add` / `edit` / `delete` 单独控制。
- 因此 edit/add/delete 在业务上依赖 list；角色分配时通过自动补全保证一致性（见 8.3）。

### 9.4 菜单与授权树（system/menu）

`sys_menu` 只负责给权限分组，鉴权链路（`UserRealm` → `sys_role_permission` → `sys_permission`）完全不经过它，新增菜单不会影响任何 `@RequiresPermissions` 判定。

```text
sys_menu (menu_id, menu_name, parent_id, path, icon, order_num, visible)
   └──< sys_permission.menu_id      # 为 NULL 时该权限归入「未分类」兜底节点
```

`SysMenuServiceImpl.buildPermTree(roleId)`：

```text
1. assertAdmin（与 SysRoleServiceImpl 一致）
2. 解析 checkedIds：
     roleId 为 null   → 空集合，全部 checked=false
     角色为 admin      → 全部 permissionId（与 assignPermissionsForRole 对 admin 强制全量一致）
     其他             → sys_role_permission 里该角色的 permissionId
3. 菜单按 parent_id / order_num / menu_id 排序，权限按 permission_id 排序后按 menu_id 分组
4. 从 parent_id=0 递归建树；父菜单不存在的菜单按顶级处理，避免脏数据导致整棵子树不可见
5. 追加「未分类」节点收拢 menu_id 为空或指向不存在菜单的权限
```

树节点 `PermTreeNodeVO` 用 `@JsonInclude(NON_NULL)`，菜单节点不输出 `permission`/`checked`，权限节点不输出 `children`。`nodeKey`（`M-1` / `P-17`）用于前端树组件，因为 `menu_id` 与 `permission_id` 各自从 1 开始会撞号。

**三者必须一致：** 数据库 `sys_permission.sys_permission` = `@RequiresPermissions("xxx")` = Shiro `isPermitted("xxx")`

---

## 10. 虚机管理（asset/host）

### 10.1 接口一览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/asset/vm` | **登录即可** | 全员可看全部虚机 |
| PUT | `/asset/vm` | **登录 + owner** | 仅 owner 可修改 |

> 无新增/删除接口。AK/SK 模式支持 GET / PUT（须对应 `vm:*` / `app:*` grant；PUT 仍受 owner 约束）。

### 10.2 数据库表 vm_host

| 字段 | 说明 |
|------|------|
| host_id | VARCHAR(36) PK |
| host_name | 虚机名（唯一） |
| os_type / os_version | 操作系统 |
| vm_ip | 虚机 IP |
| cpu_cores / memory_gb / disk_gb | 资源配置 |
| physical_host_ip | 宿主机 IP |
| lifecycle_status | 生命周期状态 |
| owner_user_id | FK → sys_user |
| network_zone | idc / cfdc |
| env | prod / dev / test |
| remark | 备注 |

### 10.3 生命周期状态机

**领域实现：** `asset/host/domain/model/VmLifecycle.java`（值对象，聚合内使用）

**兼容常量：** `asset/constant/VmLifecycleStatus.java`（`@Deprecated`，委托 `VmLifecycle`）

```text
creating → running → stopped → pending_delete → destroyed
```

**规则（`VmHost.applyUpdate` / `VmLifecycle.transitionTo`）：**

- 只能**顺序单向**流转，不可跳过、不可回退
- 相同状态允许（不变）
- `destroyed` 为终态，已销毁不可修改虚机或其应用

### 10.4 分层与核心逻辑

#### 10.4.1 调用链

```text
VmHostController
  → VmHostServiceImpl（门面）
       ├─ listVmHost  → VmHostQueryService
       └─ updateVmHost → VmHostApplicationService → VmHost 聚合 → VmHostRepository
```

#### 10.4.2 VmHostQueryService — listVmHost

```text
QueryDTO 支持：
  - hostId → 单条
  - hostName / vmIp → like
  - lifecycleStatus / ownerUserId / networkZone / env → eq
  - 分页

toVmHostVO：
  - 全部字段 + owner (OptionVO { id=userId, label=userName })
  - owner 用户名经 UserQueryPort 查询（不直注 SysUserService）
```

#### 10.4.3 VmHostApplicationService — updateVmHost

```text
1. vmHostRepository.findById(hostId)
2. host.assertOwnedBy(operatorUserId)
   → 否则 BusinessException(ASSET, "无权修改该虚机")
3. existsByHostNameExcept(hostName, hostId)
4. host.applyUpdate(command, hostNameTaken)
   → assertMutable；生命周期 transitionTo；字段赋值
5. vmHostRepository.save(host, syncAppIp)
   → 若 vmIp 变更：UPDATE vm_app SET vm_ip = ? WHERE host_id = ?
```

**事务：** `@Transactional` 在 `VmHostApplicationService.updateVmHost` 入口。

---

## 11. 应用管理（asset/app）

### 11.1 接口一览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/asset/app` | **登录即可** | 全员可看全部应用 |
| PUT | `/asset/app` | **登录 + 虚机 owner** | 仅虚机 owner 可改 |

### 11.2 数据库表 vm_app

| 字段 | 说明 |
|------|------|
| app_id | VARCHAR(36) PK |
| app_name | 应用名 |
| host_id | FK → vm_host |
| vm_ip | 冗余字段，随虚机 IP 同步 |
| deploy_path | 部署路径 |
| app_status | running / stopped |

**唯一约束：** `(host_id, deploy_path)` — 同虚机下路径不可重复

### 11.3 分层与核心逻辑

#### 11.3.1 调用链

```text
VmAppController
  → VmAppServiceImpl（门面）
       ├─ listVmApp   → 本类 + VmAppMapper（读，待抽 VmAppQueryService）
       └─ updateVmApp → VmAppApplicationService → VmHostRepository + VmHost 聚合规则
```

> **注意：** `VmAppServiceImpl` **不再**依赖 `VmHostService`；写路径通过 `VmHostRepository.findById` + `assertOperatorCanManageApps` 校验虚机 owner 与未销毁状态。

#### 11.3.2 VmAppApplicationService — updateVmApp

```text
1. vmAppMapper.selectById(appId)
2. vmHostRepository.findById(app.hostId)
3. host.assertOperatorCanManageApps(operatorUserId)
   → assertOwnedBy + 虚机未 destroyed
4. 同 hostId 下 deployPath 唯一性（排除自身）
5. 更新 appName / deployPath / appStatus
```

#### 11.3.3 VmAppServiceImpl — listVmApp

Query 支持 appId（单条）、appName（like）、hostId、vmIp、appStatus，分页返回 VmAppVO。

---

## 12. API Token（api）

### 12.1 接口一览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/token` | api:token:list | 当前用户的 Token 列表 |
| GET | `/api/token/user/{userId}` | api:token:get | 指定用户的 Token |
| GET | `/api/token/grantOptions` | api:token:add | 创建时可勾选的开放能力 |
| POST | `/api/token` | api:token:add | 创建 Token |
| DELETE | `/api/token/{tokenId}` | api:token:delete | 吊销 Token |
| GET | `/api/open/doc` | api:token:list | 开放接口动态文档元数据 |

> 不提供更新接口。路径参数 tokenId 实际为 accessKey。

### 12.2 数据库表 api_token

| 字段 | 说明 |
|------|------|
| access_key | VARCHAR(64) PK（AK） |
| user_id | FK → sys_user |
| token_name | Token 名称 |
| detail | 用途说明 |
| asset | TEXT，JSON 数组，如 `["vm:list","vm:edit","app:list"]`；兼容 `vm`、`app` |
| secret_key | SK（JWT 字符串） |
| status | 0=正常，1=已吊销 |
| expire_time | 过期时间 |

### 12.3 ApiTokenServiceImpl 核心逻辑

#### createApiToken

```text
1. LoginUserUtils.getUserId()
2. asset 格式校验：vm:* / app:*（兼容旧值 vm、app）
3. 该用户 status=0 的 Token 数 ≥ 3 → 拒绝
4. accessKey = apiJwtUtils.generateAccessKey()
5. expireTime = apiJwtUtils.defaultExpireTime()
6. secretKey = apiJwtUtils.createSecretKey(ak, userId, assets, expireTime)
7. insert api_token
8. 写 Redis `personal-demo:api-token:{accessKey}`，TTL 等于 Token 剩余有效期
9. 返回 ApiTokenVO（含 secretKey，仅创建时明文返回）
```

> 创建 Token 时不再校验创建人是否具备 `api:open:*` 系统权限；开放接口的删改由业务层校验 `ownerUserId = 当前操作用户`。

#### deleteApiToken（吊销）

```text
1. selectById(tokenId) — 实际为 accessKey
2. 校验归属当前用户
3. status = "1"（软删除，非物理删除）
4. updateById
5. 删除 Redis `personal-demo:api-token:{accessKey}`
```

> Redis 仅保存 `userId:SHA-256(secretKey)`，不保存明文 SK。缓存未命中时回源数据库并回填；吊销后先以数据库状态为准并删除缓存，旧 AK/SK 再请求会被拒绝。

#### listApiToken

仅查当前登录用户的 Token，支持 tokenName like、accessKey eq 筛选。

### 12.4 AK/SK 开放接口调用流程

```text
外部系统：
  GET /asset/vm?pageNum=1&pageSize=10
  Headers:
    X-Access-Key: ak-xxxxxxxx
    X-Secret-Key: eyJhbGciOiJIUzI1NiJ9...

服务端：
  1. JwtFilter 检测到 AK/SK 头
  2. hasAssetPermission → SK 中 asset 含 "vm"
  3. executeLogin → UserRealm 验 SK + Redis Token 缓存（未命中回源数据库）
  4. Subject authenticated，principal = userId
  5. VmHostController.list → 正常返回（无 @RequiresPermissions）
  6. PUT /asset/vm、PUT /asset/app → Application 层 owner 校验（VmHost.assertOwnedBy / assertOperatorCanManageApps），仅可改 owner=Token 所属用户的数据
  7. 无对应 asset 授权或非开放路径/方法 → JwtFilter 403
```

### 12.5 开放接口动态文档（OpenApiDocCatalog）

**文件：**

- `api/constant/OpenApiDocCatalog.java` — 已实现开放接口元数据（路径、参数、示例、grant → Shiro 映射）
- `api/constant/ApiTokenGrantCatalog.java` — Token 授出能力目录（含尚未实现的 POST/DELETE）
- `OpenApiDocController` → `GET /api/open/doc`

**逻辑：**

```text
1. 读取 OpenApiDocCatalog.implementedEntries()
2. Subject.isPermitted(requiredPermission) 过滤（如 asset:vm:list）
3. 返回 OpenApiDocVO（operations + auth 说明 + baseUrl）
```

**前端：** `ApiTokenView` 内「接口文档」Tab；示例代码与在线调试（JWT / AK/SK）。

---

## 13. 仪表盘统计（statistics）

### 13.1 接口一览

| 方法 | 路径 | scope | 权限 |
|------|------|-------|------|
| GET | `/dashboard/overview` | mine/all | mine=登录即可；all=需 dashboard:view:all |
| GET | `/dashboard/summary` | mine/all | 同 overview |
| GET | `/dashboard/kpi` | mine/all | KPI 指标 |
| GET | `/dashboard/vm/by-lifecycle` | mine/all | 虚机生命周期分布 |
| GET | `/dashboard/vm/by-env` | mine/all | 虚机环境分布 |
| GET | `/dashboard/vm/by-network-zone` | mine/all | 网络区域分布 |
| GET | `/dashboard/app/by-status` | mine/all | 应用状态分布 |
| GET | `/dashboard/trend/vm` | mine/all | 虚机新增趋势 |
| GET | `/dashboard/rank/owner` | — | 需 dashboard:view:all |
| GET | `/dashboard/vm/by-physical-host` | — | 需 dashboard:view:all |

### 13.2 scope 机制

**文件：** `statistics/constant/DashboardScope.java`

| scope | ownerUserId | 数据范围 |
|-------|-------------|----------|
| mine（默认） | 当前登录 userId | 仅 owner 是自己的虚机/应用 |
| all | null（不加 WHERE） | 全部数据，需 dashboard:view:all |

**normalizeScope 流程：**

```text
1. 空值默认 mine
2. 非法值 → BusinessException
3. all → assertViewAllPermission()
4. mine → resolveOwnerUserId() = LoginUserUtils.getUserId()
```

### 13.3 DashboardServiceImpl

#### getOverview

聚合返回 `DashboardOverviewVO`：

```text
- kpi: DashboardKpiVO
- vmByLifecycle / vmByEnv / vmByNetworkZone: PieChartVO
- appByStatus: PieChartVO
- vmCreateTrend: CategoryChartVO
- ownerRank / physicalHostDistribution: 仅 scope=all 时包含
```

#### buildKpi

| 指标 | SQL 方法 | 说明 |
|------|----------|------|
| vmHostCount | countVmHost | 虚机总数 |
| vmHostRunningCount | countVmHostRunning | running 状态虚机数 |
| vmAppCount | countVmApp | 应用总数（JOIN vm_host） |
| cpuCoresTotal | sumCpuCores | CPU 核数合计 |
| memoryGbTotal | sumMemoryGb | 内存 GB 合计 |
| userCount | countUsers | 仅 scope=all |

#### 图表 VO 结构（对齐 ECharts）

**PieChartVO：**

```json
{
  "data": [
    { "name": "running", "value": 10 },
    { "name": "stopped", "value": 3 }
  ]
}
```

**CategoryChartVO：**

```json
{
  "categories": ["2025-01", "2025-02"],
  "series": [
    { "name": "新增虚机", "data": [5, 8] }
  ]
}
```

### 13.4 DashboardMapper

使用 `@Select` 注解 + MyBatis 动态 SQL（`<script>` + `<if test='ownerUserId != null'>`）：

- `ownerUserId != null` → 追加 `WHERE owner_user_id = #{ownerUserId}`
- `ownerUserId == null` → 查全量

**注意：** JOIN 用户表时使用 `public.sys_user`。

---

## 14. 定时任务（quartz）

### 14.1 当前状态

| 组件 | 状态 |
|------|------|
| TaskRegistry | ✅ 启动扫描 `@TaskInfo` + `Task` Bean 写入 `sys_job`，并输出扫描统计日志 |
| SysJobController | ✅ 仅 list / update / changeStatus / run |
| SysJobServiceImpl | ✅ 已实现，修改/启用时同步 Scheduler |
| QuartzSchedulerService | ✅ 注册 / 更新 / 移除 / 启动加载 |
| QuartzJob + JobTaskExecutor | ✅ Cron 触发与手动执行共用执行器，写 `sys_job_log` |
| QuartzConfig | ✅ JobFactory 注入 |

**不提供新增/删除接口** — 任务定义由代码内 `@TaskInfo` 注解的 `Task` 实现类扫描注册。

### 14.2 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/monitor/job` | monitor:job:list | 分页列表；传 `jobId` 查单条 |
| PUT | `/monitor/job` | monitor:job:edit | 修改名称、Cron、描述、启用状态 |
| PUT | `/monitor/job/changeStatus?jobId=&enabled=` | monitor:job:edit | 快捷启用/停用 |
| PUT | `/monitor/job/run?jobId=` | monitor:job:edit | 手动执行一次（须已启用） |

### 14.3 任务注册与执行流程

```text
启动
  1. TaskRegistry 扫描 Task Bean
       → 日志：共 X 个 / 带 @TaskInfo Y 个 / 新写入 sys_job Z 个
       → 不存在则 insert sys_job（Cron 为空 + enabled=0）
  2. QuartzJobLoader 加载 enabled=1 的任务到 Quartz Scheduler
       → 日志：从 sys_job 加载已启用任务，共 N 条

用户修改
  1. update / changeStatus 更新 DB
  2. QuartzSchedulerService.syncJob
       enabled=1 → addOrUpdateJob（JobDetail + CronTrigger）
       enabled=0 → removeJob

Cron 触发 / 手动 run
  1. QuartzJob 或 Controller 调用 JobTaskExecutor
  2. 更新 sys_job.status（运行中/成功/失败）
  3. 写入 sys_job_log
  4. 调用 Task.execute()
```

### 14.4 字段约定

| 字段 | 含义 |
|------|------|
| `enabled` | `0` 停用 / `1` 启用；新建默认 `0`，须改 Cron 后才能启用 |
| `status` | 最近一次执行：`0` 未执行 / `1` 运行中 / `2` 成功 / `3` 失败 |
| `cronExpression` | 未配置为 `""`；启用前须填写合法表达式（含 `0 0 0 * * ?` 每天 0 点） |

### 14.5 新增 Task 步骤

1. 实现 `Task` 接口，类上加 `@Component` + `@TaskInfo(name, description)`
2. 重启应用，`TaskRegistry` 自动写入 `sys_job`
3. 管理端修改 Cron 并启用

**示例：** `quartz/task/SysReportTask.java`、`SysBackupTask.java`

### 14.6 启动排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `共 0 个` Task Bean | 无 `@Component` 的 `Task` 实现，或未扫描到 `quartz.task` 包 | 确认类实现 `Task` 并注册为 Spring Bean |
| `带 @TaskInfo 0 个` | Task 类缺少 `@TaskInfo` | 补充注解后重启 |
| `新写入 sys_job 0 个` 且库中无记录 | 同上，或 insert 失败 | 查库、看 ERROR 日志 |
| `已启用任务共 0 条` 但库中有任务 | 任务均为 `enabled=0`（新建默认停用） | 管理端改 Cron 并启用，或 `UPDATE sys_job SET enabled='1'` |
| 8080 端口占用 | systemd 服务 `personal-demo-backend.service` 已在跑 jar | IDE 使用 `dev` profile（8081），或 `sudo systemctl stop personal-demo-backend.service` |

---

## 15. 数据库设计

### 15.1 ER 关系

```text
sys_user ──< sys_user_role >── sys_role ──< sys_role_permission >── sys_permission

sys_menu ──< sys_permission (menu_id)   # 权限归属菜单，供角色授权树分组

sys_user ──< vm_host (owner_user_id)
vm_host ──< vm_app (host_id)

sys_user ──< api_token (user_id)

sys_job ──< sys_job_log (job_id)
```

### 15.2 SQL 脚本执行顺序

```text
01-create-tables.sql          # RBAC 五表
02-insert-data.sql            # admin/user 测试数据
04-asset-tables.sql           # vm_host / vm_app
05-insert-asset-data.sql      # 样例数据：15 台虚机、23 个应用（可选）
17-more-asset-data.sql        # 已有库追加样例数据（可重复执行）
06-asset-permissions.sql      # 资产权限 seed（已有库增量）
07-scaffold-tables.sql        # api_token / sys_job / sys_job_log
08-dashboard-permissions.sql  # 仪表盘权限（已有库增量）
09-fix-user-role-permissions.sql  # 修正 user 角色误分配
10-api-token-ak-sk.sql        # AK/SK 字段（已有库增量）
11-api-token-permissions.sql  # API Token 权限（已有库增量）
12-role-crud-permissions.sql  # 角色 CRUD 权限（已有库增量）
13-sys-job-enabled.sql        # sys_job enabled/bean_name（已有库增量）
14-monitor-job-permissions.sql # 定时任务权限（已有库增量）
15-sys-job-run-status.sql     # sys_job 执行状态字段（已有库增量）
16-sys-job-cron-unconfigured.sql # Cron 未配置占位改为空字符串（已有库增量）
18-sys-menu.sql               # 菜单表 + 权限归属菜单（已有库增量，须在所有权限 seed 之后执行）
19-asset-delegate-permissions.sql  # 资产平台权限整理（edit 挂菜单）
20-remove-api-open-permissions.sql  # 移除 api:open:* 嵌套授权
21-login-session.sql               # 登录设备会话表与权限
22-user-cert.sql                   # 客户端证书表、login_type、菜单 9/10
03-verify.sql                 # 验证（可选）
```

### 15.3 测试账号

| 用户 | 密码 | 角色 | 权限概要 |
|------|------|------|----------|
| admin | 123456 | admin | 全部权限 |
| user | 123456 | user | asset + system:session:list/kick + system:cert:mine |

---

## 17. 客户端证书与 mTLS 部署

### 17.1 整体链路

```text
443  HTTPS  →  SPA + /api/*（账密登录，不请求客户端证）
8443 HTTPS  →  专用 mTLS 端口（证书登录，ssl_verify_client optional_no_ca）

证书登录流程：
  登录页「证书登录」→ 整页跳转 https://{host}:8443/login/cert?redirect=1
  → TLS 握手提交 sign.p12
  → Nginx 请求客户端证书（optional_no_ca；NONE/FAILED 也转发后端）
  → 后端只接受 verify=SUCCESS；失败时 redirect=1 重定向回登录页
  → GET 自动 POST /login/cert
  → 后端指纹匹配 sys_user_cert（sign + active + 未过期）
  → 302 到 https://{host}/login#certLogin={base64 LoginVO}
  → 443 登录页解析 hash 写入 token，进入系统
```

**双层校验：** Nginx 验「是否本 CA 签发且链可信」；后端验「是否签给该用户、sign 证、未吊销」。详见 [17.2](#172-nginxhomeneoapplicationpersonaldemonginxconf)。

**为何不用 443 做 mTLS：** Nginx 的 `ssl_verify_client` 只能配在 `server` 级，443 若开启会向所有页面（含登录页）请求客户端证；Windows 浏览器选证后链校验失败时 Nginx 直接返回 **400 The SSL certificate error**，账密登录也会被波及。

**为何不用 XHR：** 浏览器仅在 **整页导航** 到 8443 时才会在 TLS 层弹出证书选择并提交客户端证；从 443 页面用 `fetch/axios` 跨端口无法触发 mTLS。

### 17.2 Nginx（`/home/neo/application/personalDemo/nginx.conf`）

**部署：** 软链 `/etc/nginx/conf.d/personalDemo.conf` → 本文件；`upstream personal_demo_backend { server 127.0.0.1:8080; }`（后端在 Windows 宿主机时改为宿主机 IP）。

**当前策略（nginx.conf）：** `ssl_verify_client optional_no_ca` — 请求客户端证书，但不在 Nginx 层直接返回 TLS 400。  
**后端职责：** 仅接受 `X-Client-Verify=SUCCESS`，再校验证书指纹白名单（`sys_user_cert`，仅 `sign` + `active`）；`NONE`/`FAILED` 在 `redirect=1` 时重定向回登录页。

**443 — 仅服务端 TLS，不启用 mTLS：**

完整配置还含 `listen 80` → 301 HTTPS、`root dist/`、gzip、`/assets/` 缓存、`try_files` SPA 回退。下面为与 mTLS 相关的摘要：

```nginx
server {
    listen 443 ssl;
    ssl_certificate     .../ca/server/personal-demo/server-chain.crt;
    ssl_certificate_key .../ca/server/personal-demo/server.key;
    # 不要在此 server 配置 ssl_verify_client / ssl_client_certificate
    root .../dist;
    location /api/ {
        proxy_pass http://personal_demo_backend/;
        # 443 不转发 X-Client-* 头
    }
    location / { try_files $uri $uri/ /index.html; }
}
```

**8443 — 证书登录专用 mTLS：**

```nginx
server {
    listen 8443 ssl;
    ssl_certificate     .../ca/server/personal-demo/server-chain.crt;
    ssl_certificate_key .../ca/server/personal-demo/server.key;

    ssl_client_certificate .../ca/client-ca-bundle.crt;
    ssl_verify_client optional_no_ca;
    ssl_verify_depth 3;

    location = /login { return 302 https://$host/login; }

    location = /debug-cert {
        proxy_pass http://personal_demo_backend/login/cert/check;
        proxy_set_header X-Client-Verify $ssl_client_verify;
        proxy_set_header X-Client-DN     $ssl_client_s_dn;
        proxy_set_header X-Client-Cert   $ssl_client_escaped_cert;
        # ... 其余 proxy_set_header 见 nginx.conf
    }
    location = /cert-check { /* 同 debug-cert */ }
    location = /login/cert {
        # OPTIONS/CORS 见 nginx.conf
        proxy_pass http://personal_demo_backend;
        proxy_set_header X-Client-Verify $ssl_client_verify;
        proxy_set_header X-Client-DN     $ssl_client_s_dn;
        proxy_set_header X-Client-Cert   $ssl_client_escaped_cert;
    }
    location / { return 404; }
}
```

| 配置项 | 说明 |
|--------|------|
| `client-ca-bundle.crt` | `intermediate-ca.crt` + `root-ca.crt` 拼接，供 Nginx 验链并下发 Acceptable CA 列表 |
| `ssl_verify_client optional_no_ca` | 请求客户端证；缺失或验链失败仍转发后端，避免停留在 Nginx 400 页面 |
| `verify=SUCCESS` | 后端唯一接受的正常值；`NONE`/`FAILED` 均作为证书登录失败处理并重定向 |

改配置后：`sudo nginx -t && sudo nginx -s reload`

### 17.3 证书存储目录

| 路径 | 用途 |
|------|------|
| `ca/root/` | 根 CA |
| `ca/intermediate/` | 中间 CA（签发客户端证） |
| `ca/client-ca-bundle.crt` | Nginx 8443 用 CA 链 |
| `ca/server/personal-demo/` | HTTPS 服务端证书（须含访问 IP 的 SAN） |
| `ca/client/users/{userId}/{applyId}/` | 用户 sign/encrypt 双证及 bundle.zip |

**签发注意（`CertIssueServiceImpl`）：** 客户端证的 issuer 须用 `X500Name.getInstance(caCert.getSubjectX500Principal().getEncoded())`，保证 issuer DN **字节序**与 intermediate CA 的 subject 一致。旧版手动拼接 DN 顺序不同会导致 Chrome/Edge（Schannel）提交证后 Nginx **400**，而 curl/OpenSSL 仍可能成功。

### 17.4 Windows 客户端导入

测试包目录：`ca_test/`（或用户下载的 bundle.zip）

| 步骤 | 操作 |
|------|------|
| 1 | `root-ca.crt` → **受信任的根证书颁发机构** |
| 2 | `intermediate-ca.crt` → **中间证书颁发机构** |
| 3 | `sign.p12` → **个人**（须显示「有对应的私钥」；**仅 sign 用于登录**） |
| 4 | 重启浏览器 |

**Chrome 不弹证书框：** 导入 `chrome-autoselect-cert.reg`（Edge 用 `edge-autoselect-cert.reg`），规则限定 `SUBJECT.CN=user` 且 `ISSUER.CN=personalDemo Intermediate CA`。

**8443 无弹窗且直接 400：** 先导入 `*-autoselect-cert-disable.reg` 关闭自动选证，再手动选择 CN=user 的 **签名证**（勿选 encrypt）。

### 17.5 验证流程

1. 账密登录 → **我的证书** 申请
2. 管理员 **证书管理** 审批（管理员弹窗记下一次性 P12 密码）
3. 用户在 **我的证书** 点击「查看 P12 密码」（仅一次），再下载 zip，按 [17.4](#174-windows-客户端导入) 导入
4. 自测：`https://{host}:8443/debug-cert` → 期望 JSON：`hasCert=true`, `ok=true`, **`verify=SUCCESS`**
5. 登录页点击 **证书登录** → 跳 8443 → 回 443 `#certLogin=...`
6. **登录设备管理** 可见 `login_type=1`

**诊断 URL（8443）：**

| URL | 说明 |
|-----|------|
| `/debug-cert` | JSON：`verify`, `dn`, `hasCert`, `ok` |
| `/cert-check` | 同上（别名） |
| `/login/cert?redirect=1` | 证书登录入口（GET 自动 POST） |

**curl 自测（WSL/服务器侧）：**

```bash
curl -sk --cert sign.pem --key sign.pem \
  -X POST "https://127.0.0.1:8443/login/cert?redirect=1" -D -
# 期望 302 Location: https://127.0.0.1/login#certLogin=...
```

### 17.6 常见问题与踩坑

| 现象 | 原因 | 处理 |
|------|------|------|
| **关闭 P12 密码弹窗后仍能反复查看** | 早期实现用 `updateById(null)` 未清库 | 已改为 `LambdaUpdateWrapper` 显式 NULL；部署新后端后重新审批或手动 `UPDATE sys_cert_apply SET p12_password=NULL` 测已领取态 |
| **443/login 弹证书框，选证后 400** | 443 误开了 `ssl_verify_client`；Windows 提交客户端证后 Nginx TLS 握手失败 | **443 不要配置 mTLS**；证书登录仅走 8443 |
| **8443/debug-cert 无弹窗直接 400** | `AutoSelectCertificateForUrls` 自动提交了不兼容的旧证或 encrypt 证 | 导入 `*-disable.reg` 关自动选证；手动选 CN=user 的 sign 证 |
| **8443 选证后仍 400，curl 却正常** | 旧版 sign.p12 的 **issuer DN 顺序**与 intermediate CA subject 不一致；Schannel 与 OpenSSL 行为不同 | 管理员 **重新签发** 证书，用户删旧证后导入新 p12 |
| **`verify=NONE`, `hasCert=false`** | 浏览器未在 TLS 层提交客户端证；`on` 下也可能直接 **TLS 失败** 而拿不到 JSON | 确认已导入 sign.p12；访问 8443 而非 443；检查是否误删个人证 |
| **登录页点证书登录无反应/跨域** | 用 axios 调 8443 无法 mTLS | 前端须 `window.location.href` 整页跳转 8443（见 `frontEnd/src/api/auth.ts`） |
| **GET /login/cert 返回 500** | 旧 JAR 无 GET 处理器 | 重新 `mvn package` 部署后端（含 GET 自动 POST 表单） |
| **浏览器不信任 HTTPS** | 服务端证书 SAN 未含访问 IP（如 `10.8.40.225`） | 重签 server 证，SAN 加入 `IP.x = 访问地址` |
| **误选 encrypt 证** | bundle 含 sign + encrypt 两张个人证 | 登录只用 **sign**；AutoSelect 规则按 CN/issuer 过滤 |
| **8443 证书缺失/链校验失败** | `verify=NONE/FAILED` | 后端拒绝证书登录；`redirect=1` 时 302 回登录页并携带 `certError` |
| **Vite `:5173` 无法测证书登录** | dev server 无 Nginx mTLS | 构建前端至 `dist/`，经 Nginx HTTPS 访问 |
| **WSL 无法 mvn package** | 环境只有 JRE 无 JDK | 在 Windows 编译 JAR 后复制到部署目录 |
| **8443 非证书路径** | 8443 无 SPA，仅证书相关路径 | `/login` → Nginx **302** 回 `https://{host}/login`；其他路径（如 `/foo`）→ **404** |

### 17.7 开发注意

- 执行 `22-user-cert.sql` 初始化表结构与菜单权限
- 中间 CA 私钥权限限制为后端进程可读
- 当前生产策略：8443 `ssl_verify_client optional_no_ca` + 后端强制 `verify=SUCCESS` + 指纹白名单
- `optional_no_ca` 不代表放宽业务校验：后端必须始终只接受 `verify=SUCCESS`
- 后端 `X509CertUtils` 对 `verify=FAILED` 的处理为代码层兜底；nginx `on` 下正常路径须先 `SUCCESS`
- 客户端导入说明见 `ca_test/README.txt`

---

### 15.4 Kingbase 特别注意

1. **sys_user 表名冲突：** Entity 用 `@TableName("sys_user")` + schema=public；手写 SQL 必须 `public.sys_user`
2. **分页方言：** PostgreSQL（`DbType.POSTGRE_SQL`）
3. **驱动 JAR：** 放 `lib/` 目录，pom.xml 用 `scope=system`

---

## 16. 开发约定与扩展指南

### 16.1 新增业务模块 Checklist

- [ ] 创建包：`controller / service / mapper / entity / dto / vo`
- [ ] Entity 加 `@TableName`，Mapper 继承 `BaseMapper`
- [ ] 在 `BackendApplication.@MapperScan` 追加 mapper 包
- [ ] Controller 返回 `AjaxResult`，列表返回 `PageResultVO`
- [ ] 写操作加 `@Log` + `@RequiresPermissions`
- [ ] Service 成功返回 void，失败抛 `BusinessException`
- [ ] SQL seed 中添加对应 permission 字符串
- [ ] 更新 `docs/API.md`

### 16.2 分层职责

| 层 | 职责 | 禁止 |
|----|------|------|
| Controller | 参数校验、权限注解、调用 Service、包装响应 | 不写业务逻辑 |
| Service（Impl） | 门面：取当前用户、委托 Application / Query | 复杂规则宜下沉 Application / Domain |
| Application | 用例编排、事务边界、load → 领域行为 → save | 不直写 HTTP 响应 |
| Domain | 聚合不变量、值对象、Repository 接口 | 不依赖 Spring / Mapper |
| Mapper / RepositoryImpl | 数据访问 | 不写业务判断 |
| Entity | 数据库映射（持久化模型） | 不含业务方法（聚合与 Entity 分离） |

> Asset 模块为上述分层的参考实现，详见 [DDD-DECOUPLING.md](./DDD-DECOUPLING.md)。

### 16.3 权限设计原则

1. **接口级：** `@RequiresPermissions` — 粗粒度，控制谁能访问接口
2. **Service 级：** `hasRole("admin")` / `isPermitted(...)` — 细粒度业务规则
3. **数据级：** 聚合根 assert（如 `VmHost.assertOwnedBy`）— 行级权限
4. **角色分配级：** `expandWithRequiredListPermissions` — 勾选 add/edit/delete 时自动补全同模块 list，保证菜单与列表 API 可用；接口鉴权仍各自独立

### 16.4 关联字段规范

- 出参：系统表关联统一 `OptionVO { id, label }`
- 入参：传 id（如 roleIds、permissionIds、ownerUserId）
- 禁止直接暴露 Entity 给前端

### 16.5 待办事项

| 项 | 说明 |
|----|------|
| 操作日志查询 API | 表 `sys_oper_log` 已有，管理端列表接口可选 |
| 定时任务 | 执行日志查询接口、Quartz JDBC JobStore（可选，当前调度元数据由 `sys_job` + 内存 JobStore 承担） |
| CorsConfig / WebConfig | 当前为空类，按需补充 CORS 规则 |
| logout | 已实现 Redis 会话删除 + `sys_login_session` 下线历史；客户端须在接口成功后清理本地 JWT |

### 16.6 调试与测试

```bash
# 全量接口测试
chmod +x scripts/test-all-api.sh
BASE_URL=http://172.21.16.1:8080 ./scripts/test-all-api.sh

# 详细输出
VERBOSE=1 ./scripts/test-all-api.sh
```

**常见问题：**

| 现象 | 排查 |
|------|------|
| 403 | 角色无 permission / 未重新登录 |
| 401 | Token 缺失或过期 |
| user 能访问 admin 接口 | 查 sys_role_permission，执行 09-fix 脚本 |
| JOIN sys_user 报错 | 改用 public.sys_user |
| Controller 404 | Rebuild Project 后重启 |
| 定时任务加载 0 条 | 仅加载 `enabled=1`；对照 TaskRegistry 扫描日志与 `SELECT * FROM sys_job` |
| 8080 已被占用 | IDE 确认激活 `dev` profile（8081），或停止 `personal-demo-backend.service` |

---

## 附录：核心文件索引

| 主题 | 路径 |
|------|------|
| 启动类 | `BackendApplication.java` |
| Shiro 配置 | `config/ShiroConfig.java` |
| JWT 过滤器 | `security/filter/JwtFilter.java` |
| Realm | `security/realm/UserRealm.java` |
| 权限切面 | `security/aspect/PermissionAspect.java` |
| 授权缓存失效 | `security/cache/AuthorizationCacheEvictor.java` |
| 用户状态变更事件 | `system/user/event/UserStatusChangedEvent.java` |
| 停用/删除级联 Listener | `auth/session/listener/`、`api/listener/`、`auth/cert/listener/`、`security/listener/` |
| 操作日志 | `common/aspect/LogAspect.java`、`common/operlog/` |
| 登录 JWT | `common/utils/JwtUtils.java` |
| API JWT | `common/utils/ApiJwtUtils.java` |
| 登录 | `auth/controller/AuthController.java` |
| 用户 | `system/user/controller/SysUserController.java` |
| 角色 | `system/role/controller/SysRoleController.java` |
| 虚机 | `asset/host/controller/VmHostController.java` |
| 应用 | `asset/app/controller/VmAppController.java` |
| VmHost 聚合 | `asset/host/domain/model/VmHost.java` |
| VmHost 写/读 | `asset/host/application/VmHostApplicationService.java`、`VmHostQueryService.java` |
| VmApp 写 | `asset/app/application/VmAppApplicationService.java` |
| UserQueryPort | `asset/port/UserQueryPort.java`、`asset/infrastructure/acl/UserQueryAdapter.java` |
| 生命周期（领域） | `asset/host/domain/model/VmLifecycle.java` |
| 生命周期（兼容） | `asset/constant/VmLifecycleStatus.java`（@Deprecated） |
| 解耦与依赖图 | `docs/DDD-DECOUPLING.md` |
| API Token | `api/controller/ApiTokenController.java` |
| 仪表盘 | `statistics/controller/DashboardController.java` |
| 定时任务 | `quartz/controller/SysJobController.java` |
| 任务扫描 | `quartz/registry/TaskRegistry.java` |
| 启动加载调度 | `quartz/registry/QuartzJobLoader.java` |
| Quartz 调度 | `quartz/service/QuartzSchedulerService.java` |
| 全局异常 | `common/exception/GlobalExceptionHandler.java` |
| RBAC SQL | `resources/sql/01-create-tables.sql` |
| 前端 API 文档 | `docs/API.md` |
