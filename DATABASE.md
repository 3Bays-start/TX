# 数据库设计

## 1. 选型与连接方式

| 环境 | 数据库 | 驱动 | 触发条件 |
| --- | --- | --- | --- |
| 生产（Docker） | MySQL 8.4（`utf8mb4` / `utf8mb4_unicode_ci`） | `asyncmy` | 设置 `MYSQL_HOST=mysql` |
| 本地开发/测试 | SQLite 3（单文件 `backend/lx_platform.db`） | `aiosqlite` | `MYSQL_HOST` 为空 |

- 连接串与降级逻辑统一收敛在 `app/config.py`（`database_url` / `is_sqlite`）。
- SQLAlchemy 2.0 异步引擎，`check_same_thread=False` 仅 SQLite 启用。
- 金额一律 `DECIMAL(18,2)`；费率 `DECIMAL(10,6)`；禁止使用 float 存储金额。
- 主键使用 `BigInteger` 自增（SQLite 方言自动降级为 `Integer`，见 `models/base.py` 的 `PK_TYPE`）。
- 命名约定（`naming_convention`）：索引 `ix_`、唯一 `uq_`、外键 `fk_`、主键 `pk_`，保证 Alembic 在 SQLite/MySQL 间可移植。

## 2. 表清单（共 48 张，已与 Alembic 初始迁移核对）

数据表由 `backend/app/models/*.py` 定义，初始迁移 `backend/alembic/versions/218608bbc4b0_initial_schema.py` 一次建齐。

### 2.1 用户与实名（5）

| 表名 | 用途 |
| --- | --- |
| `users` | 用户主表：手机号、密码哈希、状态、实名状态、风险等级、登录信息、注册渠道 |
| `user_profiles` | 用户扩展资料：性别、生日、邮箱、地区、简介（1:1） |
| `user_devices` | 用户设备登记：device_id、平台、App 版本、最后活跃时间 |
| `user_login_logs` | 登录/注册日志：类型、IP、UA、成功与否 |
| `realname_verifications` | 实名认证记录：姓名、证件号、证件照、审核状态/人/时间 |

### 2.2 账户与账务（2）

| 表名 | 用途 |
| --- | --- |
| `accounts` | 用户账户：可用/冻结/待结算余额（`DECIMAL(18,2)`）、乐观锁 version |
| `account_transactions` | 资金流水：单号、业务类型、金额、前/后余额、方向（IN/OUT）、操作者 |

### 2.3 会员（3）

| 表名 | 用途 |
| --- | --- |
| `membership_levels` | 会员等级：价格、时长、benefits/order_limits/service_permissions（JSON） |
| `memberships` | 用户当前会员：等级、生效/到期时间 |
| `membership_orders` | 会员购买订单：金额、支付状态、支付时间 |

### 2.4 商品（3）

| 表名 | 用途 |
| --- | --- |
| `product_categories` | 商品分类（支持父子） |
| `products` | 商品主表：编号、价格/市场价、描述、服务说明、库存、上下架状态 |
| `product_skus` | SKU：规格、价格、库存 |

### 2.5 订单（5）

| 表名 | 用途 |
| --- | --- |
| `orders` | 订单主表：类型（BUY/SELL/SERVICE）、金额、服务费、应付、已撮合、状态、version |
| `order_items` | 订单商品明细 |
| `order_status_logs` | 订单状态流转日志：from→to、操作者、原因 |
| `buy_orders` | 买方挂单：目标金额/已撮合金额/状态（WAITING_MATCH…） |
| `sell_orders` | 卖方挂单：可用额度/已撮合额度/状态 |

### 2.6 预约（1）

| 表名 | 用途 |
| --- | --- |
| `reservation_orders` | 预约记录：预约时间、优先级；撮合排序依据 |

### 2.7 撮合（3）

| 表名 | 用途 |
| --- | --- |
| `match_orders` | 撮合记录：match_no、父订单、买卖双方、撮合金额、状态、完成时间 |
| `match_logs` | 撮合操作日志：action、明细、操作者 |
| `matching_jobs` | 撮合扫描任务：job_id、起止时间、处理/成功/失败数、状态 |

### 2.8 费用（2）

| 表名 | 用途 |
| --- | --- |
| `fee_rules` | 服务费规则：fee_type、费率、最低/最高费用、生效时间 |
| `fee_records` | 费用记录：订单、基准金额、费率快照、费用金额 |

### 2.9 提现（2）

| 表名 | 用途 |
| --- | --- |
| `withdrawal_orders` | 提现单：金额、手续费、到账金额、银行卡信息、状态、审核/完成时间 |
| `withdrawal_logs` | 提现动作日志：CREATE/APPROVE/REJECT/COMPLETE |

### 2.10 邀请与团队（3）

| 表名 | 用途 |
| --- | --- |
| `invite_codes` | 邀请码：code、创建者、状态（UNUSED/USED/DISABLED/EXPIRED）、使用者/时间 |
| `user_relations` | 用户上下级关系：parent_id、level、path |
| `user_relation_stats` | 团队统计缓存：总人数/直属/活跃/团队订单数/团队订单额 |

### 2.11 推广（2）

| 表名 | 用途 |
| --- | --- |
| `promotion_rules` | 推广规则：rule_type、费率、状态 |
| `promotion_records` | 推广奖励记录：来源用户/订单、受益人、奖励金额、状态（PENDING/SETTLED/REVERSED）、关联流水 |

### 2.12 客服（2）

| 表名 | 用途 |
| --- | --- |
| `support_tickets` | 工单：分类、标题、内容、关联订单、优先级、状态、处理人 |
| `ticket_messages` | 工单消息：发送方类型/ID、内容、附件 |

### 2.13 申诉（2）

| 表名 | 用途 |
| --- | --- |
| `appeals` | 申诉：subject、content、evidence、状态、处理结果/人/时间 |
| `appeal_logs` | 申诉动作日志 |

### 2.14 风控（3）

| 表名 | 用途 |
| --- | --- |
| `risk_rules` | 风控规则：rule_code、等级、动作（REVIEW/FREEZE/BLOCK…）、阈值 |
| `risk_events` | 风控事件：事件号、规则、等级、动作、明细、处理状态 |
| `risk_users` | 用户风险档案：风险等级、状态、复核次数 |

### 2.15 通知与公告（2）

| 表名 | 用途 |
| --- | --- |
| `notifications` | 站内通知：类型、标题、内容、已读状态、关联业务 |
| `announcements` | 平台公告：类型、状态、发布人/时间 |

### 2.16 管理后台 RBAC（5）

| 表名 | 用途 |
| --- | --- |
| `admin_users` | 管理员：用户名、密码哈希、role_code、is_super、状态 |
| `admin_roles` | 角色：code、名称、is_system |
| `admin_permissions` | 权限点：code、name、group |
| `admin_user_roles` | 管理员-角色关联（唯一约束 uq_admin_user_role） |
| `admin_role_permissions` | 角色-权限关联（唯一约束 uq_role_permission） |

### 2.17 审计与系统（3）

| 表名 | 用途 |
| --- | --- |
| `operation_logs` | 操作审计：操作者、action、模块、目标、前后数据、原因、IP、requestId |
| `idempotency_records` | 幂等记录：key、用户、业务类型、业务 ID、响应数据 |
| `system_configs` | 系统配置：key/value（预留） |

## 3. 核心表字段说明

### `users`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | PK BigInteger | 用户 ID |
| phone | String(20) unique | 手机号 |
| password_hash | String(255) | Argon2id 哈希 |
| nickname / avatar | String | 昵称、头像 |
| status | String(20) | ACTIVE / FROZEN / DISABLED / PENDING_REVIEW |
| realname_status | String(20) | PENDING / APPROVED / REJECTED |
| risk_level | String(20) | LOW / MEDIUM / HIGH / CRITICAL |
| role | String(20) | 预留用户角色（默认 USER） |
| last_login_at / last_login_ip / register_ip / register_channel | - | 登录与注册溯源 |

### `accounts`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id / user_id | PK / FK(unique) | 账户主键与归属用户 |
| account_no | String(32) unique | 账户编号（ACC 前缀单号） |
| available_amount | DECIMAL(18,2) | 可用余额 |
| frozen_amount | DECIMAL(18,2) | 冻结余额（支付冻结、提现冻结、撮合在途） |
| pending_amount | DECIMAL(18,2) | 待结算余额（模型预留） |
| version | Integer | 乐观锁 |

### `account_transactions`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| transaction_no | String(32) unique | 流水单号（TX 前缀） |
| user_id / account_id | FK | 归属 |
| business_type | String(30) | ORDER_PAYMENT / ORDER_SETTLEMENT / SERVICE_FEE / REFUND / WITHDRAWAL / ADJUSTMENT / PROMOTION_REWARD / MEMBERSHIP_PURCHASE |
| business_id | BigInteger | 关联业务（订单/提现/撮合） |
| amount | DECIMAL(18,2) | 变动金额 |
| before_balance / after_balance | DECIMAL(18,2) | 变动前后可用余额 |
| direction | String(10) | IN / OUT |
| status | String(20) | 默认 SUCCESS |
| operator_type / operator_id | String / BigInteger | SYSTEM / ADMIN / USER 及操作者 |
| reason | String(255) | 原因 |

### `orders`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| order_no | String(32) unique | 订单号（ORD 前缀） |
| order_type | String(20) | BUY / SELL / SERVICE |
| product_id / product_name | FK / String | 商品信息（自定义金额时 product_id 为空） |
| quantity / unit_price | Integer / DECIMAL | 数量与单价 |
| total_amount | DECIMAL(18,2) | 商品/目标金额 |
| service_fee | DECIMAL(18,2) | 服务费（BUY 按费率计算） |
| payable_amount | DECIMAL(18,2) | 应付（total + fee） |
| matched_amount | DECIMAL(18,2) | 已撮合金额 |
| status | String(30) | CREATED → WAITING_PAYMENT → PAID → WAITING_MATCH → PARTIAL_MATCHED → FULL_MATCHED → PROCESSING → COMPLETED（含 CANCELLED / EXPIRED / DISPUTED / RISK_REVIEW） |
| version | Integer | 乐观锁 |
| reservation_time / expired_at | DateTime | 预约时间 / 过期时间 |

### `match_orders`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| match_no | String(32) unique | 撮合单号（MCH 前缀） |
| parent_order_id / parent_user_id | FK | 父订单（被撮合方） |
| buyer_order_id / buyer_user_id | FK | 买方（父订单即买方） |
| seller_order_id / seller_user_id | FK | 卖方 |
| match_amount | DECIMAL(18,2) | 本次撮合金额 |
| status | String(20) | ACTIVE / COMPLETED / CANCELLED |
| completed_at | DateTime | 结算完成时间 |

### `matching_jobs`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| job_id | String(40) unique | 任务号（job_ 前缀） |
| start_time / end_time | DateTime | 起止时间 |
| processed_count / success_count / failed_count | Integer | 处理/成功/失败数 |
| error_message | Text | 错误信息 |
| status | String(20) | RUNNING / COMPLETED / PARTIAL |

### `fee_rules` 与 `fee_records`

- `fee_rules.fee_type` 唯一（默认 `ORDER_SERVICE_FEE`），`rate DECIMAL(10,6)`，支持 `min_fee` / `max_fee`。
- `fee_records` 保存下单时的费率快照（rate/base_amount/fee_amount），保证**费率变更不影响历史订单**。

### `withdrawal_orders`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| withdrawal_no | String(32) unique | 提现单号（WD 前缀） |
| amount / fee / actual_amount | DECIMAL(18,2) | 申请金额 / 手续费 / 到账金额 |
| bank_name / bank_account / account_name | String | 收款信息 |
| status | String(20) | PENDING / REVIEWING / APPROVED / PROCESSING / COMPLETED / REJECTED |
| risk_level | String(20) | 申请时快照的风控等级 |
| reviewed_by / reviewed_at / processed_at / completed_at | - | 审核与完成记录 |

### `membership_levels` 与 `memberships`

- `membership_levels`：name/code 唯一，`benefits`、`order_limits`、`service_permissions` 为 JSON；种子内置 普通(BASIC, 0 元) / 高级(SILVER, 99 元/年) / VIP(299 元/年)。
- `memberships`：用户在有效期内的会员记录；购买续期时若未到期则累加 `expires_at`。

### `invite_codes` 与 `user_relations`

- `invite_codes`：`code` 唯一，`creator_id=0` 表示系统发放（不建立上下级）；状态 UNUSED/USED/DISABLED/EXPIRED。
- `user_relations`：`(user_id, parent_id, level, path)`，注册时写入 level=1 关系；推广奖励只针对 level=1 上级。

### `support_tickets` 与 `appeals`

- `support_tickets`：ticket_no 唯一，状态 OPEN / PROCESSING / WAITING_USER / RESOLVED / CLOSED。
- `appeals`：appeal_no 唯一，状态 PENDING / PROCESSING / RESOLVED / REJECTED。

### `risk_events`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| event_no | String(32) unique | 事件号（RISK 前缀） |
| rule_code | String(40) | 触发规则（如 ORDER_FREQUENCY、ORDER_CANCEL_FREQUENCY） |
| level / action | String(20) | LOW/MEDIUM/HIGH/CRITICAL；ALLOW/VERIFY/REVIEW/FREEZE/BLOCK |
| detail | Text | 明细 |
| status | String(20) | PENDING / RESOLVED / DISMISSED |

### `admin_users` 与 `admin_roles`

- `admin_users`：username 唯一，password_hash（Argon2id），`is_super` 标识超管（拥有全部权限），`role_code` 默认 ADMIN。
- `admin_roles`：系统内置 ADMIN_ORDER / ADMIN_FINANCE / ADMIN_CUSTOMER_SERVICE / ADMIN_RISK 四角色，权限点见 `app/core/permissions.py`。

### `operation_logs`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| operator_type / operator_id | String / BigInteger | 操作者类型与 ID |
| action / module | String | 动作（FREEZE/REVIEW_REALNAME/ADJUST_BALANCE/MANUAL_MATCH/UPDATE_FEE/CREATE_ADMIN…）与模块 |
| target_type / target_id | String / BigInteger | 目标对象 |
| before_data / after_data | Text | 前后数据（JSON 序列化） |
| reason / ip / user_agent / request_id | String | 原因、来源、请求上下文 |

## 4. Alembic 使用方式

项目使用 Alembic 管理 Schema 版本，异步执行（`alembic/env.py` 基于 `settings.database_url` 自动切换 MySQL/SQLite）。

```bash
cd backend

# 生成新迁移（自动对比 models 与当前库）
alembic revision --autogenerate -m "add_xxx"

# 应用迁移
alembic upgrade head

# 回退一个版本
alembic downgrade -1

# 查看当前版本与历史
alembic current
alembic history
```

- 首次迁移：`218608bbc4b0_initial_schema`（`initial schema`），已建齐全部 48 张表。
- Docker 部署：backend 容器启动命令先执行 `alembic upgrade head` 再启动 uvicorn，迁移自动完成（见 `backend/Dockerfile`）。
- 注意：模型变更后使用 `--autogenerate` 前请确保已导入 `app.models` 全部模型（`models/__init__.py` 已统一注册）。
