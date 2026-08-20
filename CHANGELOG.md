# 变更记录

本项目采用语义化版本（SemVer）。当前基线版本 **1.0.0**，对应初始迁移 `218608bbc4b0`（48 张表）与全量测试 35 通过。

## v1.0.0 — 2026-08-18

首个完整发布版本：平台业务闭环（注册 → 下单 → 支付 → 撮合 → 结算 → 提现 → 客服/申诉）与管理后台闭环全部落地，并可一键 Docker 部署。

### 新增（功能模块）

- **认证与用户**
  - 短信验证码（Redis 存储、TTL 300s、限流 10 次/60s；开发环境直接返回验证码）、注册（邀请码核销）、密码登录、JWT access/refresh 双令牌、修改密码、个人资料与实名认证（后台审核）。
  - 登录/注册审计（`user_login_logs`）、设备登记。
- **会员与商品**
  - 会员等级（普通/高级/VIP）、购买与续期（余额扣款、到期时间累加）、我的会员。
  - 商品分类、商品（价格/库存/上下架）、SKU。
- **订单与预约**
  - BUY / SELL / SERVICE 三类订单，服务费（默认 5%，`fee_rules` + 费率快照）与应付金额计算。
  - 状态机（`_ALLOWED_TRANSITIONS` + `order_status_logs`）、支付冻结、取消退款、`Idempotency-Key` 幂等创建。
  - 预约排队（撮合排序权重之一）。
- **撮合引擎**
  - A 订单 → 多 B 订单撮合：`match_orders` + `match_logs`，`match_no` 唯一。
  - 实时撮合 + 24h 周期扫描（`matching_jobs` 记录），生产 Celery Beat / 开发进程内 asyncio 调度器双通道。
  - 全额撮合自动结算：买方冻结→卖方、平台服务费入账、推广奖励发放。
- **账户与财务**
  - 账户三余额（可用/冻结/待结算）+ 全量流水（before/after balance、业务类型、操作者）。
  - 提现申请→审核（驳回自动解冻）→完成，风控等级快照与动作日志。
  - 管理员人工调账（强制原因、写操作日志）。
- **邀请与推广（合规设计）**
  - 邀请码（系统码不建关系、生成/禁用/过期）、上下级关系（level/path）与团队统计。
  - 推广奖励仅对已完成 BUY/SERVICE 真实成交发放（`promotion_rules` 默认 2%），`source_order_id` 绑定，退款/取消自动冲销（`reverse_order_reward`）。
- **客服 / 申诉 / 通知**
  - 工单双向消息、关闭；申诉处理留痕；站内通知、公告。
- **风控**
  - 风险规则/事件/用户，等级与动作（REVIEW/FREEZE/BLOCK），提现与关键操作联动。
- **管理后台**
  - Dashboard（统计概览 + 近 7 天趋势），用户/订单/撮合/财务/风控/客服/申诉/公告/邀请码管理。
  - RBAC：管理员、角色、权限点（30 个，`app/core/permissions.py`），超管标识。
  - 操作日志查询（操作者/IP/requestId/前后数据）。
- **工程基础设施**
  - Alembic 异步迁移（初始迁移一次建齐 48 张表，MySQL/SQLite 双方言）。
  - Docker Compose 9 服务编排 + 多阶段构建（web/admin）+ 健康检查 + 入口 Nginx 路由。
  - 统一响应包络（code/message/data/requestId）、全局异常映射、结构化日志与请求追踪。
  - 测试体系：35 个用例 + ruff + mypy 全绿。

### 工程加固（本轮重点）

| 类别 | 修复/加固内容 |
| --- | --- |
| 安全 | 后台全部 GET 端点补齐管理员鉴权（历史遗漏已修复），并新增回归测试 `test_admin_endpoints_require_auth` 防复发；`JWT_SECRET` 默认改为随机长串并支持环境变量注入；密码一律 Argon2id。 |
| 金额安全 | 全部金额统一 `Decimal` + `quantize(0.01)`，禁止 float；`DECIMAL(18,2)` 落库；服务费含 `min_fee/max_fee` 边界。 |
| 并发安全 | 撮合双层锁（Redis `SET NX EX` + `SELECT FOR UPDATE`）、`SUM(match_amount) <= total_amount` 算法不变量、买卖配对幂等、`orders/accounts.version` 乐观锁。 |
| 幂等 | `Idempotency-Key` 创建订单幂等，重复请求返回首次结果。 |
| 数据一致性 | `TimestampMixin` 同时设置客户端默认与 `server_default`，保证 SQLite/MySQL 时间字段一致；流水单号生成改为带锁的 `LOCK_` 前缀循环重试，避免并发冲突。 |
| 内存Redis | `MemoryRedis` 补齐 `clear/flush` 语义，保证测试隔离与缓存一致性。 |
| 安全头 | 入口 Nginx 增加 `X-Content-Type-Options`、`X-Frame-Options`、`X-XSS-Protection`、`Referrer-Policy` 与 `client_max_body_size 20m`。 |

### 已知限制

- 短信验证码当前为开发环境直接返回（`data.sms_code`），生产需接入短信网关并移除返回逻辑。
- Swagger `/docs` 为 FastAPI 默认路径，入口 Nginx 默认不代理；本地开发经 `http://localhost:8000/docs` 访问，对外暴露需补充 nginx `location /docs`。
- 推广奖励固定为一级上级（level=1），多级层级不在本期范围（符合合规边界）。
- 测试环境使用 SQLite + MemoryRedis，行锁/分布式锁语义建议在生产部署前用 MySQL/Redis 做一次真机回归。

### 后续规划（Roadmap）

- 短信网关、第三方支付充值、银行卡校验。
- 撮合策略可配置（优先级权重、撮合轮次）。
- 商品库存与 SKU 结算联动、评价体系。
- 后台二步验证（OTP）、审计报表导出。
- 覆盖率门禁、MySQL/Redis 真机集成测试。
