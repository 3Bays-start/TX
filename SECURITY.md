# 安全设计

本文档描述 LX Platform 的安全架构与合规加固要点。代码依据见 `backend/app/core/`、`app/dependencies.py`、`docker-compose.yml`、`nginx/nginx.conf`。

## 1. 认证与令牌

| 项 | 设计 | 依据 |
| --- | --- | --- |
| 算法 | JWT `HS256`，对称密钥 `JWT_SECRET` | `app/core/security.py` |
| Access token | 默认 2 小时（`JWT_ACCESS_EXPIRE=7200`），payload 含 `sub`(用户ID)/`type=access`/`iat`/`exp` | 同上 |
| Refresh token | 默认 30 天（`JWT_REFRESH_EXPIRE=2592000`），`type=refresh`，仅用于换取新 access | 同上 |
| 令牌校验 | `decode_token` 校验签名、过期（`TOKEN_EXPIRED`）、类型（access/refresh 不可混用） | 同上 |
| 传输 | 一律 `Authorization: Bearer <token>`，服务端从请求头提取 | `auth_service._extract_token` |
| 密钥 | 生产必须更换默认值，使用 `openssl rand -hex 32` 生成；通过环境变量注入 | `config.py` / `docker-compose.yml` |

> 生产安全要求：`JWT_SECRET` 不得使用默认值。Docker 部署时在 `.env` 中设置，未设置时 compose 会回退到内置默认字符串。

## 2. 密码存储

- 使用 **Argon2id**（`argon2-cffi` 的 `PasswordHasher`），每次哈希自动加盐。
- `users.password_hash`、`admin_users.password_hash` 均为 Argon2id 哈希，不存明文。
- 校验失败与无效哈希统一返回失败，不泄露哈希格式信息。
- 注册密码强度：8~64 位且必须同时包含字母与数字（Pydantic `field_validator`）。

## 3. RBAC 权限模型与后台全接口鉴权

- 权限点：`app/core/permissions.py` 定义了 30 个权限码，按分组归类（用户 / 订单 / 客服 / 财务 / 风控 / 商品会员 / 系统）。
- 角色：`admin_roles` 支持多角色；系统内置四个角色：订单管理员、财务管理员、客服、风控专员（`seed_system_roles`）。
- 关联：`admin_user_roles`（管理员-角色）、`admin_role_permissions`（角色-权限），均带唯一约束防重。
- 超级管理员：`is_super=true` 或 `role_code=SUPER_ADMIN` 拥有全部权限。
- 依赖：`require_permission(permission)` 提供权限点校验；冻结用户等敏感操作额外校验 `SUPER_ADMIN`。
- **后台全接口鉴权（无越权）**：除 `POST /admin/login` 外，全部后台端点都依赖 `admin_service_me`（内部调用 `get_current_admin`），匿名访问一律 401。该行为已被回归测试 `test_admin_endpoints_require_auth` 覆盖，防止未来新增 GET 端点时遗漏鉴权。
- 用户侧水平越权防护：订单/工单/通知/申诉等查询接口均以 `current_user.id` 过滤，`get_order(db, order_id, user_id)` 校验归属。

## 4. 前端不可信原则

- 订单状态只由后端状态机推进：`order_service.transition` 依据 `_ALLOWED_TRANSITIONS` 白名单流转，并记录 `order_status_logs`。
- 前端（web/admin）不提供任何直接修改订单状态的接口；用户端仅有「支付 / 取消」两个触发动作，管理员仅有「人工撮合」。
- 金额由后端以 `Decimal` 计算并 quantize，前端只做展示；接口金额字段一律以字符串返回，避免浮点精度丢失。

## 5. 金额安全：Decimal + 事务

- 禁止 float 参与金额计算；金额统一 `decimal.Decimal` 并 `quantize(Decimal("0.01"))`（`account_service._amount`、`fee_service.calc_fee`）。
- 数据库金额字段统一 `DECIMAL(18,2)`（费率 `DECIMAL(10,6)`）。
- **任何余额变化必须同时写流水** `account_transactions`（before/after balance），且在同一 DB 事务内提交。
- 账户读写使用 `SELECT ... FOR UPDATE`（`get_account_for_update`）行级锁；`accounts.version` 乐观锁兜底。
- 撮合结算（买方冻结→卖方、平台服务费）在单个事务内完成，任一失败整体回滚。

## 6. 并发与防超卖

- 撮合入口先取 Redis 分布式锁 `lock:matching:order:{order_id}`（`SET NX EX`，TTL 10s）。
- 父订单与候选卖方均 `FOR UPDATE`；每次撮合 `min(卖方剩余, 买方剩余)`，`remaining` 递减，从算法上保证 `SUM(match_amount) <= total_amount`。
- 同一 (父订单, 卖方订单) 配对幂等判重，`match_no` 唯一索引兜底。
- 支付接口状态机限制：仅 `WAITING_PAYMENT` 可支付，重复支付返回 `ORDER_INVALID_STATUS`。
- 幂等：`POST /orders` 支持 `Idempotency-Key` 头，落 `idempotency_records`，重复请求返回首次结果。

## 7. 限流

| 接口 | 限制 | 实现 |
| --- | --- | --- |
| `POST /auth/sms-code` | 10 次 / 60 秒（按 IP） | `RateLimiter(10, 60)` → Redis INCR + EXPIRE |
| `POST /auth/login` | 10 次 / 60 秒（按 IP） | 同上 |
| 通用 | `rate_limit(limit, window)` 依赖可挂载到任意接口 | `app/dependencies.py` |

无 Redis 时由进程内 `MemoryRedis` 提供同样的 `incr/expire` 语义，本地开发与测试不受影响。

## 8. 敏感信息不出网

- `docker-compose.yml` 中 MySQL、Redis、RabbitMQ 均**不发布宿主机端口**，仅存在于内部 `internal` 网络。
- 唯一公网端口为 Nginx `:80`，仅代理 web/admin/api 三条路径。
- MySQL/Redis/RabbitMQ 均设置了强密码（compose 默认占位符 `CHANGE_ME`，部署时必须替换）。
- 后端不对外暴露数据库连接串；配置通过环境变量注入。
- 个人信息脱敏工具 `mask_sensitive`（手机号/姓名/证件号）可用于日志与响应展示。

## 9. HTTPS 建议

- 生产环境应在 Nginx 前加挂 TLS（反向代理 / CDN 终止均可），将 80 端口重定向到 443。
- 如直接在 Nginx 上终止 TLS，请同时开启 `X-Forwarded-Proto: https` 透传（入口 nginx 已设置 `proxy_set_header X-Forwarded-Proto $scheme`），确保 `_client_ip` 依赖的 `x-forwarded-for` 可靠取值。
- `client_max_body_size 20m` 已配置，防止超大上传。

## 10. 日志与操作审计

- 结构化日志：每请求生成 `request_id`（写入响应头 `X-Request-Id`），`user_id`/`admin_id` 通过 ContextVar 注入日志行。
- 操作审计：调账、冻结/解冻、实名审核、人工撮合、费率修改、管理员创建/更新等写入 `operation_logs`，含操作者、动作、模块、目标、前后数据、原因、IP、requestId。
- 登录审计：`user_login_logs` 记录登录/注册来源与成败；管理员 `last_login_at` 更新。
- 建议：将后端 `stdout` 日志接入集中式日志（如 ELK/Loki），审计表定期归档。

## 11. 数据备份建议

- 数据卷：`mysql_data`（`/var/lib/mysql`）、`redis_data`（`/data`，appendonly）。
- 建议每日 `mysqldump --single-transaction` 全量备份 + binlog 增量；定期做恢复演练。
- Redis 开启 AOF（compose 已 `--appendonly yes`）。
- 备份文件存放于独立存储，且不包含未脱敏密钥之外的个人信息明文（如已有，请加密落盘）。

## 12. 上线检查清单

- [ ] `.env` 中已替换 MySQL / Redis / RabbitMQ 密码与 `JWT_SECRET`（`openssl rand -hex 32`）
- [ ] `APP_ENV=production`、`DEBUG=false`
- [ ] 后台默认账号 `superadmin` 已修改默认密码（或通过 `ADMIN_INIT_PASSWORD` 覆盖后首登改密）
- [ ] HTTPS 已启用，80 端口重定向
- [ ] 完成全量回归测试（`pytest`、`ruff`、`mypy`）
- [ ] 建立每日备份与恢复演练
