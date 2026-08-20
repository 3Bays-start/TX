# 系统架构

本文描述 LX Platform 的整体架构、模块划分、核心业务流程、撮合算法与并发安全设计、数据库事务边界，以及合规设计说明。

## 1. 总体架构

```text
                            ┌──────────────────── Internet ────────────────────┐
                            │                                                     │
                            ▼                                                     ▼
                    ┌──────────────┐                                    ┌──────────────────┐
                    │   Nginx :80  │  docker-compose 唯一对外入口       │  HTTPS（建议在     │
                    │  (ingress)   │  仅此端口暴露公网                 │   前置 LB/网关终止）│
                    └──────┬───────┘                                    └──────────────────┘
                           │
            ┌──────────────┼─────────────────┐
            │              │                 │
            ▼              ▼                 ▼
   ┌────────────────┐ ┌───────────┐ ┌────────────────┐
   │ web (Vue+Vant) │ │  admin    │ │  backend        │  FastAPI + SQLAlchemy async
   │  用户端 SPA     │ │  管理后台   │ │  :8000          │
   │  nginx:80      │ │  nginx:80 │ │  /api/v1/*      │
   └────────────────┘ └───────────┘ │  /health        │
                                    └───┬────────┬────┘
                                        │        │
               ┌────────────────────────┘        └───────────────────────┐
               ▼                                                          ▼
      ┌───────────────┐  ┌─────────────────┐  ┌──────────────────────┐  ┌─────────────────┐
      │ MySQL 8       │  │ Redis 7         │  │ RabbitMQ 3           │  │ Celery           │
      │ 数据持久化     │  │ 锁/限流/验证码   │  │ Broker               │  │ worker + beat    │
      │（内网不暴露）  │  │（内网不暴露）    │  │（内网不暴露）          │  │ 24h 扫描任务      │
      └───────────────┘  └─────────────────┘  └──────────────────────┘  └─────────────────┘

   降级模式（本地开发 / 测试）：
   · MYSQL_HOST 为空          → SQLite（aiosqlite）
   · REDIS_HOST 为空          → 进程内 MemoryRedis（锁/限流/验证码仍可用）
   · CELERY_ENABLED=false     → 进程内 asyncio 调度器（app/tasks/scheduler.py）
```

- 所有内部服务（MySQL / Redis / RabbitMQ / backend / celery / web / admin）只连接 docker 内部 `internal` 网络，**不发布任何对外端口**。
- 唯一公网暴露为 Nginx `:80`，按路径路由：`/` → web，`/admin/` → admin，`/api/` → backend，`/health` → backend。
- 请求上下文（`request_id` / `user_id` / `admin_id`）由 `app/main.py` 的中间件写入 ContextVar，贯穿日志、审计与响应头 `X-Request-Id`。

## 2. 模块划分

| 模块 | 位置 | 职责 |
| --- | --- | --- |
| auth | `services/auth_service.py`、`api/v1/auth.py` | 短信验证码、注册（校验邀请码）、登录、JWT 签发/刷新、当前用户与当前管理员依赖 |
| users | `services/user_service.py`、`api/v1/users.py` | 个人资料、实名认证提交、修改密码、团队统计与成员列表 |
| invite | `services/invite_service.py`、`api/v1/invites.py` | 邀请码生成/查询/禁用、注册时核销并建立上下级关系 |
| membership | `api/v1/memberships.py` | 会员等级查询、购买/续期（扣减可用余额）、我的会员 |
| product | `models/product.py`、`api/v1/memberships.py` | 商品分类、商品列表/详情（仅上架商品可见） |
| order | `services/order_service.py`、`api/v1/orders.py` | 订单创建（BUY/SELL/SERVICE）、支付、取消、订单状态机（`transition`） |
| reservation | `services/reservation_service.py`、`api/v1/reservations.py` | 预约登记，撮合排序依据之一 |
| matching | `services/matching_service.py`、`api/v1/reservations.py` | 撮合引擎、实时撮合、24h 扫描、结算与完成、撮合日志/任务 |
| account | `services/account_service.py`、`api/v1/accounts.py` | 账户（可用/冻结/待结算）、入账/出账/冻结/解冻/结算、全量流水、管理员调账 |
| fee | `services/fee_service.py` | 服务费规则与计算（费率快照）、费用记录 |
| withdrawal | `services/withdrawal_service.py`、`api/v1/finance.py` | 提现申请（冻结）、审核（通过/驳回解冻）、完成（出账） |
| promotion | `services/promotion_service.py` | 推广奖励（绑定真实成交订单）、退款/取消冲销助手 |
| support | `services/support_service.py`、`api/v1/support.py` | 客服工单与消息 |
| appeal | `services/appeal_service.py`、`api/v1/support.py` | 申诉提交与处理 |
| risk | `services/risk_service.py`、`api/v1/admin.py` | 风险事件记录、风险等级联动、冻结/禁用动作、订单频次检查 |
| notification | `services/notification_service.py`、`api/v1/support.py` | 站内通知、公告 |
| admin | `services/admin_service.py`、`api/v1/admin.py` | Dashboard、用户/订单/撮合/财务/风控/客服/申诉管理、管理员与角色管理、日志查询 |
| audit | `services/audit_service.py` | 操作日志写入（前后数据、IP、requestId） |
| tasks | `tasks/` | Celery 应用、撮合扫描任务、进程内降级调度器 |

## 3. 核心流程

### 3.1 注册

```text
用户输入手机号
  → POST /auth/sms-code：生成 6 位验证码写入 Redis（TTL 300s），开发环境直接返回
  → POST /auth/register：
      1) 校验手机号未注册（唯一索引）
      2) 校验短信验证码（Redis 校验通过即删除，防重放）
      3) 核销邀请码（use_invite_code：UNUSED → USED；系统邀请码 creator_id=0 不建关系）
      4) 创建用户（密码 Argon2id 哈希）+ 自动开户（ensure_account）
      5) 如邀请人非系统，写入 user_relations（level=1，path=/父/子）
      6) 记录注册登录日志，签发 access + refresh token
```

### 3.2 下单 → 支付 → 撮合 → 结算

```text
创建订单 POST /orders（Idempotency-Key 幂等）
  · BUY：total + service_fee(默认5%) → payable_amount，状态 WAITING_PAYMENT
  · SELL/SERVICE：状态直接 WAITING_MATCH（服务方挂单）
支付 POST /orders/{id}/pay
  · 冻结：available → frozen（ORDER_PAYMENT），状态 PAID → WAITING_MATCH
  · 触发实时撮合 try_match_order
撮合 match_order（见 §4 并发安全）
  · 选取等待匹配的卖方（排除本人），按 预约时间→创建时间→id 升序
  · 每次最小撮合 min(卖方剩余, 买方剩余)，创建 match_orders + match_logs
  · 更新双方 matched_amount，订单 PARTIAL_MATCHED / FULL_MATCHED
结算 _settle_and_complete（全额匹配时）
  · 每笔撮合：买方冻结 → 卖方可用（ORDER_SETTLEMENT，双流水）
  · 平台服务费：买方冻结 → 平台账户(PLATFORM_USER_ID=0)（SERVICE_FEE）+ fee_records 费率快照
  · 订单 FULL_MATCHED → PROCESSING → COMPLETED
  · 完成后 settle_order_reward：给一级上级发放推广奖励（绑定真实成交，见 §6）
```

### 3.3 24h 扫描（兜底撮合）

```text
Celery Beat（生产） / 进程内调度器（降级）
  scan-pending-orders-daily：
    扫描 WAITING_MATCH / PARTIAL_MATCHED 订单 → 逐个重新调用 match_order
    记录 MatchingJob（job_id / 处理数 / 成功数 / 失败数 / 状态 COMPLETED|PARTIAL）
  scan-complete-processing-daily：
    将到期的 PROCESSING 订单推进为 COMPLETED（服务周期结束）
生产间隔 MATCH_SCAN_INTERVAL_PROD=86400s；开发环境 MATCH_SCAN_INTERVAL=60s 便于观察。
```

### 3.4 提现

```text
POST /withdrawals
  1) 实名必须 APPROVED
  2) 风控检查：HIGH/CRITICAL 拦截（RISK_REVIEW_REQUIRED）
  3) 创建提现单（PENDING），立即冻结可用余额（WITHDRAWAL）
后台审核 POST /admin/withdrawals/{id}/review
  · 通过 → APPROVED
  · 驳回 → 解冻退款，记录 review_reason
后台完成 POST /admin/withdrawals/{id}/complete
  · APPROVED/PROCESSING → COMPLETED，冻结正式出账（写流水）
全程 WithdrawalLog 记录 CREATE/APPROVE/REJECT/COMPLETE 动作。
```

### 3.5 申诉 / 工单

```text
工单：POST /support/tickets → 用户/客服在 ticket_messages 双向回复 → 后台关闭
申诉：POST /appeals（可关联 order_id）→ 后台 POST /admin/appeals/{id}/process
      → approve 则 RESOLVED，否则 REJECTED；全程 AppealLog 留痕
```

## 4. 撮合算法与并发安全

撮合引擎位于 `services/matching_service.py`，核心不变量：**`SUM(match_amount) <= order.total_amount`，绝不超额、绝不重复撮合、绝不产生负余额**。

### 4.1 撮合算法

```text
match_order(order_id):
  1. Redis 分布式锁 lock:matching:order:{order_id}（防多 Worker 并发进入同一订单）
  2. SELECT ... FOR UPDATE 锁定父订单（保证状态读取与金额修改在同一事务内）
  3. 状态仅允许 WAITING_MATCH / PARTIAL_MATCHED；计算剩余 = total - matched
  4. 候选卖方：
     - SellOrder.status = WAITING_MATCH
     - Order.status ∈ (WAITING_MATCH, PARTIAL_MATCHED)
     - Order.user_id != 买方
     - 排序：coalesce(预约时间, 创建时间) 升序 → 创建时间升序 → SellOrder.id 升序
     - 对候选整批 SELECT ... FOR UPDATE（锁住卖方行，防止并发超额）
  5. 逐卖方面额 = min(卖方剩余, 买方剩余)：
     - 幂等防重：同一 parent_order_id + seller_order_id 已存在 match_orders 则跳过
     - 写 match_orders（唯一 match_no）+ match_logs
     - 更新 sell.matched_amount / order.matched_amount / version
  6. 若有撮合 → 状态 PARTIAL_MATCHED；全额 → _settle_and_complete
```

### 4.2 并发安全手段（五层防线）

| 层 | 手段 | 说明 |
| --- | --- | --- |
| 分布式锁 | Redis `SET NX EX`（`LockContext`，默认 TTL 10s，重试 30 次×100ms） | 同一订单同一时间只有一个匹配者；无 Redis 时由 `MemoryRedis` 进程内锁兜底 |
| 行锁 | MySQL `SELECT ... FOR UPDATE`（父订单 + 候选卖方 + 账户） | 事务内锁定，杜绝读到脏中间状态 |
| 幂等 | `match_orders` 对 `(parent_order_id, seller_order_id)` 判重；`match_no` 唯一索引 | 同一买卖配对只撮合一次 |
| 乐观锁 | `orders.version`、`accounts.version` 自增 | 检测并发写冲突 |
| 业务不变式 | 每次撮合 `min(available, remaining)`，`remaining` 递减至 0 即停 | 从算法上保证不超额 |

账户侧（`account_service.py`）：所有余额变化都通过 `get_account_for_update`（FOR UPDATE）+ 同时写 `account_transactions` 流水（before/after balance），同一 DB 事务内完成。

## 5. 数据库事务边界

- 请求级事务：`get_db` 依赖成功则 `commit`，异常则 `rollback`。业务服务只做 `flush`，不在服务内提交，从而把「创建订单 + 生成 BuyOrder/SellOrder + 状态日志」等收进同一事务。
- 撮合扫描任务：`scan_pending_orders` 使用**每订单独立 Session** 提交（`match_order` → `commit`，异常 `rollback` 并计数），单订单失败不影响其他订单；`MatchingJob` 最终态单独写回。
- 支付：`freeze + 状态机 transition(PAID→WAITING_MATCH) + 实时撮合` 在同一个 `get_db` 事务内，任一失败整体回滚，不会出现「扣了钱却未进入撮合」。
- 结算：`_settle_and_complete` 内所有 `settle_from_frozen`（买方/卖方/平台账户流水）+ 状态机 + `fee_records` + `promotion` 在同一个事务内，要么全部生效要么全部回滚。
- 提现：申请（冻结）→ 审核（驳回解冻）→ 完成（出账）各自独立事务，由状态机约束（`PENDING/REVIEWING → APPROVED/REJECTED`，`APPROVED/PROCESSING → COMPLETED`），杜绝重复审核/重复出账。

## 6. 合规设计说明

- **无资金池**：资金只发生在「买方→卖方/平台」的订单结算与「平台→用户」的推广奖励/退款解冻，不设任何由用户资金构成的资金池。
- **无固定层级返佣**：推广奖励仅发给**一级**上级（`user_relations.level == 1`），且只对 `BUY/SERVICE` 真实成交订单发放。
- **无虚构收益**：推广奖励率来自 `promotion_rules`（默认 2%），必须存在已完成的真实订单（`source_order_id` 绑定），`promotion_records.status` 从 `PENDING → SETTLED` 并关联 `account_transactions`。
- **退款/取消可冲销**：`reverse_order_reward` 按 `source_order_id` 冲销已结算奖励（`SETTLED → REVERSED` 并反向出账），确保奖励不与不存在的成交共存。
- **费用透明**：服务费按 `fee_rules` 计算并落 `fee_records`（含费率快照），费率变更不影响历史订单。
- **后台留痕**：调账、冻结、实名审核、人工撮合、费率修改、管理员变更等操作全部写入 `operation_logs`（前后数据、原因、IP、requestId）。
- **前端不可信**：订单状态仅由后端状态机（`transition` + `_ALLOWED_TRANSITIONS`）推进，前端不提供任何直接改写订单状态的接口。
