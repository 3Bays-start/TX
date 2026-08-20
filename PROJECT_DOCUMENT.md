# LX Platform 项目文档（详细版）

> 生成日期：2026-08-19
> 覆盖：项目概述、技术栈、架构、目录、数据库、核心流程、API、安全（含密码存储形式）、凭证上传现状、部署运维、测试，以及**全面问题排查报告**与修复建议。
> 问题部分区分「已实测验证」与「代码审查发现（未实测）」。

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [仓库目录结构](#3-仓库目录结构)
4. [三端职责与运行方式](#4-三端职责与运行方式)
5. [核心业务模型与数据库](#5-核心业务模型与数据库)
6. [订单状态机与撮合结算流程](#6-订单状态机与撮合结算流程)
7. [API 清单](#7-api-清单)
8. [认证与密码存储形式（问题一）](#8-认证与密码存储形式问题一)
9. [订单凭证上传现状（问题二）](#9-订单凭证上传现状问题二)
10. [安全设计现状](#10-安全设计现状)
11. [部署与运维](#11-部署与运维)
12. [测试体系](#12-测试体系)
13. [全面问题排查报告](#13-全面问题排查报告)
14. [修复建议与优先级](#14-修复建议与优先级)
15. [相关文档索引](#15-相关文档索引)

---

## 1. 项目概述

LX Platform 是一个前后端分离的订单撮合与会员服务平台：

- **用户端**（Vue3 + Vant）：注册/登录、实名认证、商品浏览、预约、创建援助订单（BUY / SELL / SERVICE）、支付、查看撮合进度、账户/提现/团队/客服/申诉/通知。
- **管理后台**（Vue3 + Element Plus + ECharts）：Dashboard、用户、订单、撮合、账户财务、提现审核、费率、推广奖励、风控、客服工单、申诉、公告、管理员/角色/权限、操作日志。
- **后端**（FastAPI + SQLAlchemy 2 async + Pydantic v2）：统一鉴权、账务、撮合引擎、状态机、定时扫描、Alembic 迁移。

业务核心：用户通过**邀请码**注册（账号+密码，无需手机短信），完成**实名认证**后可下单；撮合引擎将「A 订单 → 多 B 订单」自动撮合并**冻结→结算**资金；平台按成交收取**服务费**（默认 5%），并为真实成交给上级发放**推广奖励**（默认 2%）。

> 合规边界：推广奖励必须与真实商品/服务成交绑定；退款/取消时冲销；不存在资金池、固定层级返佣与虚构收益。

### 近期功能变更记录（信用等级替代会员等级）

- 会员等级体系已从 API/前端中移除（后端 `memberships.py` 删除、`router.py` 不再挂载、seed 不再播种；`membership_levels` 等表仍保留在库中但不再使用）。
- 新增**信用等级**体系：`credit_levels` 表 + `users.completed_order_count`，按「已完成订单数」自动升级（普通信用 0 / 铜牌 3 / 银牌 10 / 金牌 30 / 钻石 80 笔）。
- 撮合结算时**买卖双方订单都计入完成数**（卖方订单原先不会流转到 COMPLETED，已修复）。

---

## 2. 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.12 + FastAPI 0.115 + SQLAlchemy 2.0（async）+ Pydantic v2 + Alembic |
| 数据库 | MySQL 8（utf8mb4，生产）/ SQLite + aiosqlite（本地开发与测试） |
| 缓存/锁/限流 | Redis 7（无 Redis 时降级为进程内 MemoryRedis） |
| 任务 | Celery + Celery Beat + RabbitMQ（关闭时降级为进程内 asyncio 调度器） |
| 用户端 | Vue 3 + TypeScript + Vite + Pinia + Vant 4 |
| 管理后台 | Vue 3 + TypeScript + Element Plus + ECharts |
| 密码哈希 | Argon2id（argon2-cffi） |
| JWT | PyJWT（HS256） |
| 测试 | pytest + pytest-asyncio + httpx TestClient |
| 质量 | ruff + mypy |
| 部署 | Docker Compose + Nginx 1.27 |

---

## 3. 仓库目录结构

```text
TX/
├── .env.example            # 环境变量样例（后端全部配置，注意全部为占位值）
├── docker-compose.yml      # nginx / backend / celery-worker / celery-beat / mysql / redis / rabbitmq / web / admin
├── start-dev.ps1           # Windows 本地一键启动（后端:8000 / web:5174 / admin:5173）
├── README.md               # 总览与快速开始
├── PROJECT_DOCUMENT.md     # 本文档
├── ARCHITECTURE.md / DATABASE.md / API.md / SECURITY.md / DEPLOYMENT.md / TESTING.md / CHANGELOG.md / API.md
├── backend/
│   ├── Dockerfile          # 启动前 alembic upgrade head，再 uvicorn
│   ├── requirements.txt    # 依赖（fastapi/uvicorn/sqlalchemy/aiosqlite/asyncmy/alembic/pyjwt/argon2/redis/celery/python-multipart/httpx/pytest/ruff/mypy）
│   ├── pyproject.toml      # pytest / ruff / mypy 配置
│   ├── alembic.ini + alembic/env.py + alembic/versions/   # 5 个迁移
│   ├── app/
│   │   ├── main.py         # 入口、CORS、异常处理、/health、lifespan（init_db + seed + scheduler）
│   │   ├── config.py       # pydantic-settings 配置（读取 .env）
│   │   ├── database.py     # 异步引擎/会话/Base
│   │   ├── dependencies.py # 分页/幂等/限流
│   │   ├── seed.py         # 种子：superadmin、RBAC、费率、推广规则、信用等级、示例商品、系统邀请码
│   │   ├── core/           # security(JWT+Argon2id) / permissions / response / exceptions / logging
│   │   ├── models/         # 全部 SQLAlchemy 模型（见 §5）
│   │   ├── schemas/        # Pydantic 请求/响应
│   │   ├── services/       # 业务服务（撮合/账务/订单/认证/提现/风控/推广/信用/客服/申诉/邀请/通知/费用/预约/审计）
│   │   ├── api/v1/         # auth/users/invites/products/credit/orders/reservations/accounts/finance/support/banners/admin
│   │   ├── tasks/          # celery_app / matching_tasks / order_tasks / scheduler(进程内兜底)
│   │   └── utils/          # 单号与幂等 / redis_client(含 MemoryRedis)
│   └── tests/              # unit / integration / matching / api，共 41 个用例
├── web/                    # 用户端（Vue3 + Vant）
│   ├── Dockerfile / nginx.conf / vite.config.ts（dev 代理 /api → localhost:8000）
│   └── src/ api/ stores/ router/ views/
└── admin/                  # 管理后台（Vue3 + Element Plus）
    ├── Dockerfile / nginx.conf / vite.config.ts（base=/admin/，dev 端口 5173）
    └── src/ api/ stores/ router/ layout/ views/
```

---

## 4. 三端职责与运行方式

### 4.1 端口与访问

| 端 | 开发地址 | 生产（Docker） |
| --- | --- | --- |
| 后端 | http://localhost:8000（/docs 为 Swagger，/health 健康检查） | http://localhost/api/ |
| 用户端 | http://localhost:5174/ | http://localhost/ |
| 管理后台 | http://localhost:5173/admin/ | http://localhost/admin/ |

### 4.2 开发运行

- 后端：`cd backend` → 激活 `.venv` → `pip install -r requirements.txt` → `alembic upgrade head` → `uvicorn app.main:app --host 127.0.0.1 --port 8000`（未配置 MYSQL_HOST/REDIS_HOST/CELERY_ENABLED=false 时自动降级为 SQLite + 内存 Redis + 进程内调度器）。
- 用户端：`cd web && npm run dev`（端口 5174，`/api` 代理到 8000）。
- 管理后台：`cd admin && npm run dev`（端口 5173，base `/admin/`）。
- 一键脚本：`powershell -ExecutionPolicy Bypass -File .\start-dev.ps1`（自动拉起三端并做健康检查）。

### 4.3 默认账号

| 账号 | 说明 |
| --- | --- |
| `superadmin` / `Admin@123456` | 超级管理员（可在 .env 用 `ADMIN_INIT_USERNAME/PASSWORD` 覆盖） |
| 普通用户 | 需通过邀请码注册（seed 生成 10 个系统邀请码 `creator_id=0`） |

---

## 5. 核心业务模型与数据库

数据访问：开发环境为 SQLite（`backend/lx_platform.db`）；生产为 MySQL（`MYSQL_HOST` 非空时切换，URL 带 `charset=utf8mb4`）。

### 5.1 Alembic 迁移链（5 个，均已应用）

1. `218608bbc4b0_initial_schema` — 初始 48 张表
2. `7f3a9c21d4b8_users_username_parent_switch` — 用户名登录 + 上级切换
3. `c5d8e2f1a9b3_create_banners_table` — 公告横幅
4. `e4f0a1b2c3d4_add_usdt_address` — 提现订单增加 usdt_address
5. `f5a1b2c3d4e5_credit_levels` — credit_levels 表 + users.completed_order_count（含回填）

### 5.2 主要表

| 域 | 表 |
| --- | --- |
| 用户 | `users`（含 `password_hash`、`username`、`completed_order_count`）、`user_profiles`、`realname_verifications`、`user_devices`、`user_login_logs` |
| 邀请 | `invite_codes`、`user_relations`（树）、`user_relation_stats` |
| 账户 | `accounts`（available/frozen/version）、`account_transactions` |
| 订单 | `orders`（order_no/type/status/total/service_fee/payable/matched/version）、`order_items`、`order_status_logs`、`buy_orders`、`sell_orders` |
| 撮合 | `match_orders`（parent↔seller）、`match_logs`、`matching_jobs` |
| 预约 | `reservation_orders` |
| 商品 | `products`、`product_categories`、`product_skus` |
| 费率 | `fee_rules`、`fee_records` |
| 信用 | `credit_levels`（name/code/min_orders/description/sort_order/status） |
| 提现 | `withdrawal_orders`（含 usdt_address）、`withdrawal_logs` |
| 推广 | `promotion_rules`、`promotion_records` |
| 客服/申诉 | `support_tickets`、`ticket_messages`（attachments 为字符串）、`appeals`、`appeal_logs` |
| 风控 | `risk_rules`、`risk_events`、`risk_users` |
| 通知 | `notifications`、`announcements`、`banners` |
| 后台 | `admin_users`、`admin_roles`、`admin_permissions`、`admin_role_permissions`、`admin_user_roles` |
| 审计 | `operation_logs`、`idempotency_records`、`system_configs` |
| 会员（废弃） | `memberships`、`membership_levels`、`membership_orders`（表保留，功能下线） |

---

## 6. 订单状态机与撮合结算流程

### 6.1 订单类型与状态

- 类型：`BUY`（买方/提供资金）、`SELL`（卖方/接收资金）、`SERVICE`（服务类）。
- 状态链：`CREATED → WAITING_PAYMENT → PAID → WAITING_MATCH → PARTIAL_MATCHED → FULL_MATCHED → PROCESSING → COMPLETED`；可分支 `CANCELLED / EXPIRED / DISPUTED / RISK_REVIEW`。
- 允许转换表见 `app/services/order_service.py:20`。

### 6.2 主流程

1. **下单**：BUY 时计算服务费（默认 5%），`payable_amount = 金额 + 费`，状态 `WAITING_PAYMENT`；SELL/SERVICE 创建即 `WAITING_MATCH`（SELL 建 `SellOrder`，BUY 和 SERVICE 建 `BuyOrder`）。
2. **支付**：可用余额 → 冻结（`ORDER_PAYMENT`），状态 → `WAITING_MATCH`，触发**实时撮合** `try_match_order`。
3. **撮合**：买方订单（`WAITING_MATCH`/`PARTIAL_MATCHED`）按「预约时间升序 → 创建时间升序 → id 升序」匹配非本人的卖方订单；单笔撮合量 = min(买方剩余, 卖方可用)。防并发：Redis 锁 + `SELECT FOR UPDATE` + 幂等去重 + version 自增。
4. **结算**（`_settle_and_complete`）：买方冻结 → 卖方可用（`ORDER_SETTLEMENT`）；买方服务费 → 平台账户（`SERVICE_FEE` + `fee_records` 快照）；买方订单 → `FULL_MATCHED → PROCESSING → COMPLETED`；**卖方订单额度用尽时同步完成**（计入信用等级完成数，不重复发放推广奖励）。
5. **扫描任务**（进程内调度器，开发 60s / 生产 24h）：
   - `scan_pending_orders`：重新撮合 WAITING_MATCH/PARTIAL_MATCHED 订单。
   - `scan_complete_processing`：把 PROCESSING 订单推进为 COMPLETED。

### 6.3 信用等级

- 规则：`credit_levels.min_orders` 升序，取「已完成订单数 ≥ min_orders」的最高档。
- 完成订单计数字段：`users.completed_order_count`，由 `order_service.transition()` 在 `to_status == COMPLETED` 时 +1。
- 接口：`GET /api/v1/credit/level` 返回当前档位/下一档/进度/还需几笔。

---

## 7. API 清单

统一前缀 `/api/v1`；统一响应包络 `{code:0, message, data, requestId}`；分页统一 `{items, total, page, page_size}`；鉴权统一 `Authorization: Bearer <token>`。

### 7.1 用户端

| 模块 | 端点 |
| --- | --- |
| 认证 | `POST /auth/register`、`POST /auth/login`（限流 10/60s）、`POST /auth/refresh`、`POST /auth/switch-user`、`GET /auth/me` |
| 用户 | `GET /users/me`、`PUT /users/me/profile`、`POST/GET /users/me/realname`、`POST /users/me/password`、`GET /users/team/summary`、`GET /users/team/switchable`、`GET /users/team` |
| 邀请码 | `POST /invites/codes`、`GET /invites/codes`、`POST /invites/codes/{id}/disable` |
| 商品 | `GET /products/categories`、`GET /products`、`GET /products/{id}` |
| 信用 | `GET /credit/level` |
| 订单 | `POST /orders`、`GET /orders`、`GET /orders/{id}`、`POST /orders/{id}/pay`、`POST /orders/{id}/cancel`、`GET /orders/{id}/match` |
| 预约 | `POST /reservations`、`GET /reservations`、`GET /reservations/matching/status/{order_id}` |
| 账户 | `GET /accounts`、`GET /accounts/transactions` |
| 财务 | `POST /finance/withdrawals`（amount + usdt_address）、`GET /finance/withdrawals`、`GET /finance/fees`、`GET /finance/promotion/records` |
| 客服/通知 | `POST/GET /support/tickets`、`GET /support/tickets/{id}`、`POST /support/tickets/{id}/messages`、`POST/GET /support/appeals`、`GET /support/notifications`、`POST /support/notifications/{id}/read`、`POST /support/notifications/read-all`、`GET /support/announcements` |
| 其他 | `GET /banners` |

### 7.2 管理后台（全部挂 `/admin` 前缀）

| 模块 | 端点 |
| --- | --- |
| 认证 | `POST /admin/login`、`GET /admin/me` |
| 概览 | `GET /admin/dashboard` |
| 用户 | `GET /admin/users`、`GET /admin/users/{id}`、`POST /admin/users/{id}/freeze`、`POST /admin/users/{id}/unfreeze`、`POST /admin/users/{id}/adjust`（余额调整）、`POST /admin/realname/{ver_id}/review` |
| 订单 | `GET /admin/orders`、`GET /admin/orders/{id}`、`POST /admin/orders/{id}/manual-match` |
| 撮合 | `GET /admin/matching`、`GET /admin/matching/jobs` |
| 财务 | `GET /admin/accounts/{user_id}`、`GET /admin/transactions`、`GET /admin/withdrawals`、`POST /admin/withdrawals/{id}/review`、`POST /admin/withdrawals/{id}/complete`、`GET /admin/fees`、`PUT /admin/fees/{fee_type}`、`GET /admin/fees/records`、`GET /admin/promotions` |
| 风控 | `GET /admin/risk/events`、`POST /admin/risk/events/{id}/review` |
| 客服/申诉 | `GET /admin/tickets`、`POST /admin/tickets/{id}/reply`、`POST /admin/tickets/{id}/close`、`GET /admin/appeals`、`POST /admin/appeals/{id}/process` |
| RBAC | `GET/POST /admin/admins`、`PUT /admin/admins/{id}`、`GET/POST /admin/roles`、`PUT /admin/roles/{id}`、`GET /admin/permissions` |
| 其他 | `GET /admin/logs`、`POST /admin/invites`（系统邀请码）、`GET/POST /admin/announcements` |

> 注意：`admin.py` 中 `request: Request = None` 为类型标注缺陷（FastAPI 注入正常，见 §13 问题 5.6）。

---

## 8. 认证与密码存储形式（问题一）

### 8.1 结论

**数据库中以 Argon2id 加盐哈希存储，绝无明文。**

- 算法：`argon2.PasswordHasher()`（argon2-cffi，默认 **Argon2id**，内置随机盐）。
- 位置：`users.password_hash` / `admin_users.password_hash`（`String(255)`）。
- 入口：`app/core/security.py` 的 `hash_password()` / `verify_password()`。
- 写入路径：`auth_service.register`、`admin_service` 创建/改密、`users.py /me/password`、`seed.py` 初始化超管。
- 校验路径：`auth_service.login`、`admin_service.admin_login`、`users.py /me/password`。
- 盐与参数已内嵌在哈希串中（如 `$argon2id$v=19$m=...$t=...$p=...$...`），无需单独存盐。

> 已实测确认：数据库中 `password_hash` 全部为 `$argon2id$...` 格式，无明文；不存可逆密文。

### 8.2 注意事项

- 密码强度校验：`schemas/auth.py` 要求 8~64 位（Register/ChangePassword 均有校验）。
- 管理员密码与用户密码同算法；`ADMIN_INIT_PASSWORD` 为默认占位值，生产必须修改（见 §13 问题 1.3）。

---

## 9. 订单凭证上传现状（问题二）

### 9.1 结论

**当前系统没有任何「订单撮合成功后上传凭证」的功能，用户端、管理后台、后端均不存在；与后台更谈不上联通。**

> **状态更新（2026-08-19）：该功能已按 §9.2 方案实现并验证通过**，见下方补充说明。

依据（已核实）：

1. **后端**：全库无任何文件上传端点（无 `UploadFile`、无 `/files`、无 multipart 处理路由）；`Order`/`BuyOrder`/`SellOrder`/`MatchOrder` 等模型**均无凭证/证据字段**。
2. **配置是死配置**：`UPLOAD_DIR / UPLOAD_MAX_SIZE / UPLOAD_ALLOWED_EXT`（`config.py:54-57`）定义后**无任何代码消费**。
3. **用户端**：`web/src` 无 Vant `Uploader`，无凭证相关 UI/API；`OrderDetail.vue`/`OrderMatch.vue` 仅展示订单与撮合状态。
4. **管理后台**：无凭证查看/审核界面；唯一与"附件"沾边的是工单回复的 `attachments` 字段，且它只是**手工填写的字符串 URL/文本**，不是文件上传。
5. 实名证件、申诉证据等字段（`document_front/back`、`evidence`）同样只是字符串持久化，无上传能力。

### 9.2 若需实现该功能（建议方案）

- 后端：新增 `POST /api/v1/upload`（受鉴权），消费 `UPLOAD_DIR/UPLOAD_MAX_SIZE/UPLOAD_ALLOWED_EXT`，文件名白名单 + 大小限制 + 目录隔离 + 静态托管 `/uploads/*`。
- 数据：`orders`（或 `buy_orders`）增加 `proof_urls`（JSON/文本，逗号分隔）字段 + `proof_submitted_at`；撮合完成后（`FULL_MATCHED`/`PROCESSING` 阶段）允许买方上传凭证。
- 用户端：`OrderMatch.vue` 增加 Vant Uploader，提交后调上传接口并把 URL 写入订单。
- 管理后台：`OrderDetailView.vue` 展示凭证图片（`<el-image>`）并可下载，作为人工审核依据。
- 迁移：新增 Alembic migration 加字段。

### 9.3 已实现（2026-08-19）

- 后端：`POST /api/v1/upload`（用户鉴权，扩展名白名单 + 10MB 上限 + 按用户目录隔离 + UUID 文件名），静态托管 `/uploads/*`（`main.py` mount）。
- 数据：`orders.proof_urls`（逗号分隔 URL）+ `orders.proof_submitted_at`，迁移 `a1b2c3d4e5f7`。
- 订单接口：`POST /api/v1/orders/{id}/proof` 绑定凭证，仅限订单本人、仅 BUY/SERVICE、且状态为 `FULL_MATCHED`/`PROCESSING`/`COMPLETED`（撮合成功后）；URL 必须指向 `/uploads/` 前缀，拒绝外链。
- 用户端：`OrderDetail.vue` 撮合完成后显示 Vant Uploader 上传/删除/预览凭证。
- 管理后台：`OrderDetailView.vue` 新增「订单凭证」卡片，`<el-image>` 预览 + 大图查看。
- 验证：ruff/mypy 通过、pytest 49 通过（新增 6 个上传/凭证用例）、端到端上传→静态访问→绑定→后台可见全链路正常。

---

## 10. 安全设计现状

- **密码**：Argon2id（§8）。
- **JWT**：HS256，`sub=用户/管理员 id`，payload 含 `type=access|refresh`；access 2h / refresh 30d。
- **RBAC**：`admin_users/admin_roles/admin_permissions` 表 + `require_permission` 依赖定义（⚠️ 未接入接口，见 §13 问题 1.4）。
- **并发**：Redis 锁（`LockContext`）+ `SELECT ... FOR UPDATE` + 幂等去重 + version 字段。
- **脱敏**：`mask_sensitive` 对手机号/姓名/身份证脱敏（部分接口）。
- **限流**：用户登录 `RateLimiter(10, 60)`（⚠️ 见 §13 问题 1.8/1.10）。
- **审计**：`operation_logs` 记录操作者/IP/requestId/前后数据。

---

## 11. 部署与运维

### 11.1 Docker Compose（9 服务）

nginx / backend / celery-worker / celery-beat / mysql / redis / rabbitmq / web / admin。backend 容器启动前执行 `alembic upgrade head`。入口 nginx 路由：`/` → web、`/admin/` → admin、`/api/` → backend、`/health` → backend。

### 11.2 生产部署步骤

1. `cp .env.example .env` 并**修改所有占位密钥**（JWT_SECRET、MYSQL_PASSWORD、REDIS_PASSWORD、RABBITMQ_PASSWORD、ADMIN_INIT_PASSWORD）。
2. `docker compose up -d --build`。
3. `docker compose ps` 检查全部 healthy。

### 11.3 数据备份与升级

- 备份：MySQL `mysqldump`；SQLite 直接拷贝 `lx_platform.db`。
- 升级：`alembic upgrade head`（容器启动自动执行）。

> ⚠️ 生产环境必须处理 §13 中的高危问题（尤其越权漏洞 1.1、默认密钥 1.3），否则**不建议暴露公网**。

---

## 12. 测试体系

- 栈：pytest + pytest-asyncio + httpx TestClient（内存 SQLite，conftest 建表+种子）。
- 目录：`tests/unit`（security/fee/invite/credit）、`tests/integration`（auth_flow/account/order_matching/withdrawal）、`tests/matching`（concurrency）、`tests/api`（admin_api）。
- **当前结果：41 passed，1 warning**（fastapi/testclient 的 httpx 弃用警告，可忽略）。
- 质量门禁：`ruff check` + `mypy`（`requirements.txt` 已含 ruff/mypy；pyproject.toml 配置）。
- 常用命令：
  ```bash
  cd backend
  .venv\Scripts\python.exe -m pytest
  .venv\Scripts\python.exe -m ruff check app tests
  .venv\Scripts\python.exe -m mypy app
  ```

---

## 13. 全面问题排查报告

> 标记：**[已实测]** = 本次已通过运行验证；**[审查]** = 代码/配置审查发现，未做运行验证。严重度：高/中/低。

### 13.1 安全

**1.1【高·已实测】普通用户令牌可越权访问全部管理接口（身份撞库）**

- 位置：`app/services/auth_service.py:156-166`（`get_current_admin`）、`app/api/v1/auth.py` 登录签发、`app/seed.py` 创建 superadmin。
- 现象：`get_current_admin` 只 `db.get(AdminUser, int(payload["sub"]))`，不校验令牌签发身份；用户和管理员签发的是**同一种** `type=access` 令牌。`admin_users` 与 `users` 各自独立自增主键——seed 创建的 superadmin 必然是 `id=1`，而注册的第一个普通用户 id 也是 `1`。因此**任意普通用户用自己的令牌请求 `/admin/*`，会被解析成 id=1 的 superadmin**。
- 实测：用普通用户 `parent_a`（users.id=1）的 token 请求 `GET /admin/me`，返回 `{id:1, username:"superadmin", role_code:"SUPER_ADMIN"}` 及全部权限。**管理后台整体失守。**
- 修复：JWT payload 加主体类型（`role: user|admin`），`get_current_admin` 强制校验；或给 AdminUser 用独立序列主键。

**1.2【高·审查】CORS 全放开且允许携带凭据**

- `app/main.py:44-50`：`allow_origins=["*"]` + `allow_credentials=True`。生产应改为域名白名单，或关闭 credentials。

**1.3【高·审查】JWT_SECRET/SECRET_KEY/数据库口令/初始超管密码全为占位默认值，无 .env**

- `app/config.py:23,32,44,49,61`；仓库根目录与 backend 均无 `.env`。部署未注入环境变量时，JWT 密钥公开可猜（可伪造任意 token）、初始超管口令已知。生产必须强制校验非占位值。

**1.4【高·审查】RBAC 权限点定义后未应用到任何接口**

- `app/core/permissions.py` 定义了 `require_permission` 但全库无消费方；`admin.py` 中提现审核/出账、余额调整、费率修改、人工撮合、风控处理、管理员/角色管理等高危接口都只做「是管理员即放行」。低权限管理员可执行一切操作。

**1.5【中·审查】冻结用户需超管，解冻无校验**

- `admin.py:196-199` freeze 校验 `role_code == "SUPER_ADMIN"`，`:202-211` unfreeze 无校验，权限不对称。

**1.6【中·审查】提现缺最小金额与每日限额校验**

- `withdrawal_service.py:18-50` 仅校验 `amount <= 0`；`WITHDRAW_MIN_AMOUNT`/`WITHDRAW_DAILY_LIMIT`（config.py:68-69）无任何消费方。可提 0.01 元、不限当日总额。

**1.7【高·审查】系统邀请码 `creator_id=0` 违反外键约束（生产 MySQL 必崩）**

- `invite_service.py:23`、`seed.py:137`：`InviteCode.creator_id` FK→`users.id`，但系统邀请码用 `creator_id=0`。SQLite 默认不启用外键所以本地/测试能跑；MySQL 下 seed 和 `/admin/invites` 会直接外键报错。需改为可空 NULL 或虚拟系统占位用户。

**1.8【中·审查】注册无限流；登录限流可被伪造 IP 绕过**

- `auth.py:24-32` register 无限流；login 限流键基于 `X-Forwarded-For` 首值（`auth.py:79-83`），未配置可信代理时可伪造绕过，暴力破解无防护。

**1.9【中·审查】Redis 内存降级模式下锁无法正常释放**

- `redis_client.py:134-147`：`RedisClient.acquire_lock` 内存分支用自己的 token，而 `MemoryRedis.acquire_lock`（:55-62）内部另生成 token，`release_lock` 比对永不等，只能等 10s TTL 自动过期。无 Redis 环境下撮合并发会持锁 10s 且重试 3s 后可能抛超时。

**1.10【中·审查】管理员登录无限流**

- `admin.py:70-84` 无 `RateLimiter`，后台口令可无限爆破。

**1.11【中·审查】提现审核/完成无并发防护**

- `withdrawal_service.py:53-91` 先读后改、无 `with_for_update`；两管理员并发审核/完成可能重复出账或状态错乱。

### 13.2 一致性 / 事务

**2.1【高·审查】SERVICE 订单从不冻结资金，撮合结算必然失败**

- `order_service.py:99-123`：SERVICE 创建即 `WAITING_MATCH`（不进入支付），却又建 `BuyOrder`；`matching_service._settle_and_complete` 用 `settle_from_frozen` 从买方**冻结余额**扣款（`account_service.py:229-243`，不足抛 `FROZEN_INSUFFICIENT`）。故**所有 SERVICE 订单撮合后结算必失败**（seed 的三个服务商品都无法完成交易闭环）。

**2.2【中·审查】`scan_complete_processing` 无条件把 PROCESSING 订单推进为 COMPLETED**

- `matching_service.py:251-265`：不校验 `expired_at`/服务期。生产扫描 24h，任何进入 PROCESSING 的订单都会被强制完成，违背 `service_days` 语义。

**2.3【中·审查】乐观锁 version 只自增、从不校验**

- 多处 `version += 1`，但全库无 `WHERE version = ?` 冲突检测。真正的并发保护靠 FOR UPDATE + Redis 锁；文档声称的"乐观锁"名不副实。

**2.4【低-中·审查】幂等记录无唯一约束**

- `utils/misc.py:33-66` + `IdempotencyRecord` 无 `(key,user,business_type)` 唯一索引，并发重复请求仍可能重复创建订单。

**2.5【低·审查】推广奖励发放无幂等保护**

- `promotion_service.py:44-67`：`PromotionRecord` 无 `(source_order_id, rule_type)` 唯一约束，重放可能重复发放。

**2.6【低·审查】`reverse_order_reward` 定义后从未被调用**（`promotion_service.py:70-92`）。

**2.7【低·审查】`check_order_risk` 定义后从未被调用**（`risk_service.py:86-112`），下单/取消未接入风控。

### 13.3 配置

**3.1【高·审查】无 .env，生产配置依赖默认占位值**（同 1.3）。

**3.2【中-低·审查】上传配置是死配置**（UPLOAD_* 无任何代码消费，与 §9 结论一致）。

**3.3【低·审查】`DEBUG` 默认 True**：生产未设 `DEBUG=false` 会输出全部 SQL 日志。

**3.4【低·审查】`expires_in=7200` 硬编码**：`auth.py:30`、`auth_service.py:91,122,135`、`admin.py:79`，与 `JWT_ACCESS_EXPIRE` 配置脱节。

**3.5【低·审查】`SECRET_KEY` 是死配置**：定义但无消费方（JWT 用 `JWT_SECRET`）。

### 13.4 业务漏洞

**4.1【中·审查】管理端无权限地暴露用户敏感信息**：`admin.py:147-185` user_detail 返回注册 IP、实名姓名/证件号（未脱敏）；叠加 1.4 权限未生效，任何管理员可查看。

**4.2【中·审查】订单过期机制缺失**：定义了 `EXPIRED` 状态与转换，但无定时任务触发"超时未支付→EXPIRED"，未支付订单永远停在 WAITING_PAYMENT。

**4.3【低·审查】提现驳回/完成并发组合错误**：1.11 的业务后果延伸，可能出现"先完成出账、后驳回解冻"。

**4.4【无问题】工单附件/申诉证据/实名证件字段不会被当作文件路径使用**（无路径穿越/任意文件读取风险，已确认）。

### 13.5 代码缺陷

**5.1【高·审查】`func.date("now", "-30 day")` 为 SQLite 专用语法，生产 MySQL 报错**

- `user_service.py:43`（`/users/team/summary`）、`risk_service.py:95,106`。MySQL 的 `DATE()` 只接受一个参数。生产切 MySQL 后 `/users/team/summary` 必崩。

**5.2【低-中·审查】分页 total 用全量加载计数**：多处先 `SELECT` 全表再 `len()`，数据量大时内存/IO 浪费。

**5.3【低·审查】`ticket_detail` 冗余查询**：`support.py:74` 的 `list_tickets` 结果完全未使用。

**5.4【低·审查】时间统一性**：业务层普遍 `datetime.now()`（naive 本地时区），与 JWT 的 `datetime.now(dt.UTC)` 混用，容器 `TZ=Asia/Shanghai`，环境变化时排序/过期判断会偏移。建议统一时区。

**5.5【无问题】`request.client` 为 None 已处理**；真正风险是 1.8 的 X-Forwarded-For 信任。

**5.6【低·审查】`request: Request = None` 类型标注缺陷**：`admin.py:62,192,206,218,237,338`（FastAPI 注入正常，标注不严谨）。

**5.7【无问题确认】无 SQL 注入、金额精度正确**：全库查询均为 SQLAlchemy 参数化绑定；金额统一 `Decimal` + `quantize(0.01)`。

### 13.6 总体结论

- **架构与账务基础质量较好**：统一响应/异常、服务分层、Decimal 记账、FOR UPDATE + Redis 锁、状态机 + 状态日志；无 SQL 注入、无浮点金额、无竞态扣减。
- **但存在 4 个高危且生产必然触发的问题**：
  1. **管理员撞库越权**（1.1，已实测）——最优先，等于管理后台失守。
  2. **SERVICE 订单撮合结算必失败**（2.1）。
  3. **生产 MySQL 下 seed 外键错误 + `/team/summary` SQL 语法报错**（1.7、5.1）。
  4. **默认密钥/初始口令全为占位值**（1.3）。
- **中危**集中在权限体系未生效（1.4/1.5/4.1）、提现风控缺失（1.6/1.11）、内存锁释放缺陷（1.9）、扫描破坏服务期语义（2.2）。

---

## 14. 修复建议与优先级

| 优先级 | 问题 | 修复方向 |
| --- | --- | --- |
| P0 | 1.1 越权 | JWT payload 加主体类型并强制校验；管理后台未修复前勿公网暴露 |
| P0 | 2.1 SERVICE 结算失败 | 统一订单语义：SERVICE 走支付冻结，或建 SellOrder 而非 BuyOrder |
| P0 | 1.3 / 3.1 默认密钥 | 强制环境变量、启动校验占位值、首启强制改密 |
| P0 | 1.7 外键错误 / 5.1 SQLite 语法 | 系统邀请码 creator_id 改 NULL；日期计算改方言无关写法 |
| P1 | 1.4 RBAC 未生效 | 全部管理接口接入 `require_permission` |
| P1 | 1.6 提现风控 | 实现最小金额 + 日限额 |
| P1 | 1.9 内存锁 | 内存分支复用同一 token |
| P1 | 1.11 提现并发 | `with_for_update` / 条件更新 |
| P1 | 2.2 扫描语义 | 按 expired_at/service_days 判断后再 COMPLETED |
| P2 | 1.2/1.5/1.8/1.10/1.11/4.1/4.2/5.2/5.3/5.4/5.6 | 按安全/健壮性逐一加固 |
| 待办 | §9 凭证上传 | ~~若产品需要，按 §9.2 方案实现~~ **已完成（2026-08-19）**，见 §9.3 |

> **修复状态（2026-08-19）**：P0/P1 全部完成并经回归验证；P2 已做 CORS、注册/登录限流、realname 脱敏、冗余查询清理、类型标注（`request: Request = None` 修复）；剩余可暂缓项：4.2 支付超时扫描（需产品配置）、5.2 COUNT 分页优化、5.4 时区统一。验证结果：ruff/mypy 通过、pytest 43 通过、迁移 `a1b2c3d4e5f6` 已应用、越权复测（普通用户 token 访问 `/admin/me` 返回 401）、SERVICE 下单→支付→撮合全流程正常、web/admin 构建通过。

---

## 15. 相关文档索引

- `README.md` — 总览与快速开始
- `ARCHITECTURE.md` — 系统架构与核心流程
- `DATABASE.md` — 数据库设计与 Alembic
- `API.md` — 完整 API 清单
- `SECURITY.md` — 安全设计
- `DEPLOYMENT.md` — 部署与运维
- `TESTING.md` — 测试
- `CHANGELOG.md` — 版本变更记录