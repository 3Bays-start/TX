# API 文档

LX Platform 后端 API（v1）基于 FastAPI，统一前缀 `/api/v1`。本文档整理自 `backend/app/api/v1/*.py` 与 `app/core/response.py`。

## 1. 通用约定

### 1.1 Base URL

- Docker 部署：`http://localhost/api/v1`
- 本地开发：`http://localhost:8000/api/v1`

### 1.2 统一响应包络

所有接口（含成功与失败）返回统一 JSON 结构：

```json
{
  "code": 0,
  "message": "success",
  "data": { },
  "requestId": "req_xxxxxxxxxxxxxxxxxxxx"
}
```

| 字段 | 说明 |
| --- | --- |
| code | 成功为整数 `0`；失败为错误码字符串（如 `AUTH_INVALID`、`INSUFFICIENT_BALANCE`） |
| message | 提示信息 |
| data | 业务数据（成功时返回，可能为 `null`） |
| requestId | 请求追踪 ID，同时写入响应头 `X-Request-Id` |

常见业务错误码：`AUTH_INVALID`、`TOKEN_EXPIRED`、`PERMISSION_DENIED`、`USER_FROZEN`、`USER_DISABLED`、`INVITE_CODE_INVALID/USED/EXPIRED`、`ORDER_NOT_FOUND`、`ORDER_INVALID_STATUS`、`MATCH_OVERFLOW`、`INSUFFICIENT_BALANCE`、`WITHDRAWAL_INVALID`、`RISK_REVIEW_REQUIRED`、`VALIDATION_ERROR`、`RATE_LIMITED` 等（完整见 `app/core/response.py`）。

### 1.3 HTTP 状态码

| 状态码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 业务错误（错误码在 body 中） |
| 401 | 未认证 / 令牌无效或过期 |
| 403 | 权限不足 / 用户被冻结或禁用 |
| 404 | 资源不存在 |
| 422 | 参数校验失败（`VALIDATION_ERROR`） |
| 500 | 系统内部错误 |

### 1.4 鉴权约定

- 需登录接口：请求头携带 `Authorization: Bearer <access_token>`（token 类型为 `access`，默认 2 小时有效）。
- 刷新：用 `refresh` 类型 token 调 `POST /auth/refresh` 换取新 access。
- 管理员接口：同一 Bearer 头，但 token 主体为 `admin_users.id`，且仅管理员签发。
- 匿名访问需鉴权接口返回 401；被冻结/禁用用户返回 403。

### 1.5 分页参数约定

- 查询参数：`page`（≥1，默认 1）、`page_size`（1~100，默认 20）。
- 响应结构：`{ "items": [...], "total": N, "page": p, "page_size": s }`（部分接口返回 `unread` 等附加字段）。
- 过滤参数（如 `status`、`business_type`、`user_id`）以各端点说明为准。

### 1.6 幂等约定

- `POST /api/v1/orders` 支持请求头 `Idempotency-Key`。重复 key 会返回首次创建结果（`data.duplicated=true`），不重复下单。
- 实现基于 `idempotency_records` 表（key + user_id + business_type 联合判定）。

---

## 2. 认证 `auth`

### 2.1 发送短信验证码 — 公开

`POST /api/v1/auth/sms-code`

- 限流：10 次/60 秒（按 IP）。
- 请求：`{"phone": "13800000000"}`
- 响应：`{"phone": "...", "sms_code": "123456"}`（开发环境直接返回验证码，验证码同时写入 Redis，TTL 300 秒；接入短信网关后可改为不返回）。

### 2.2 注册 — 公开

`POST /api/v1/auth/register`

- 请求：`{"phone", "sms_code", "invite_code", "password", "nickname"}`（密码 8~64 位且必须同时含字母与数字）。
- 响应：`TokenPair`（见下）。注册即自动开户并核销邀请码。

### 2.3 登录 — 公开

`POST /api/v1/auth/login`

- 限流：10 次/60 秒。
- 请求：`{"phone", "password"}`；成功写登录日志并更新 `last_login_at`。

### 2.4 刷新令牌 — 公开

`POST /api/v1/auth/refresh`

- 请求：`{"refresh_token": "..."}`；响应新的 `TokenPair`。

`TokenPair` 结构：`{"access_token", "refresh_token", "token_type": "bearer", "expires_in": 7200}`

### 2.5 当前用户信息 — 需用户 token

`GET /api/v1/auth/me`

- 响应含 `id, phone, nickname, avatar, status, realname_status, risk_level, membership_name, created_at`。

---

## 3. 用户 `users`（均需用户 token）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/users/me` | 用户信息 + 资料（含 profile） |
| PUT | `/api/v1/users/me/profile` | 更新资料（nickname/avatar/gender/email/region/bio 可部分提交） |
| POST | `/api/v1/users/me/realname` | 提交实名认证 `{name, id_number, document_front, document_back}` → PENDING |
| GET | `/api/v1/users/me/realname` | 查询本人实名状态与审核原因 |
| POST | `/api/v1/users/me/password` | 修改密码 `{old_password, new_password}` |
| GET | `/api/v1/users/team/summary` | 团队统计 `{total_team, direct_count, active_count, team_order_count, team_order_amount}` |
| GET | `/api/v1/users/team` | 团队成员分页（phone 已脱敏） |

---

## 4. 邀请码 `invites`（均需用户 token）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/invites/codes` | 生成邀请码 `{count, expires_in_days?}` |
| GET | `/api/v1/invites/codes` | 我的邀请码列表 |
| POST | `/api/v1/invites/codes/{code_id}/disable` | 禁用本人未使用的邀请码 |

---

## 5. 会员与商品 `membership` / `product`

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/v1/memberships/levels` | 公开 | 上架会员等级列表（含 benefits/order_limits/service_permissions） |
| POST | `/api/v1/memberships/purchase` | 用户 | 购买/续期会员 `{level_id}`，从可用余额扣款，返回 `{order_id, level_name}` |
| GET | `/api/v1/memberships/my` | 用户 | 我的会员（等级/到期时间） |
| GET | `/api/v1/products/categories` | 公开 | 启用中的商品分类 |
| GET | `/api/v1/products` | 公开 | 上架商品分页（仅 status=ON） |
| GET | `/api/v1/products/{product_id}` | 公开 | 商品详情（仅上架可见） |

---

## 6. 订单 `orders`（均需用户 token）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/orders` | 创建订单（支持 `Idempotency-Key` 头）。请求：`{product_id?|amount?, order_type: BUY\|SELL\|SERVICE, quantity?, reservation_time?, remark?}`。BUY 计算服务费并进入 WAITING_PAYMENT；SELL/SERVICE 直接 WAITING_MATCH |
| GET | `/api/v1/orders` | 我的订单分页（可选 `status` 过滤） |
| GET | `/api/v1/orders/{order_id}` | 订单详情（含 status_logs 与 matches） |
| POST | `/api/v1/orders/{order_id}/pay` | 支付：冻结可用余额并进入撮合队列，随后实时撮合 |
| POST | `/api/v1/orders/{order_id}/cancel` | 取消：已支付则解冻退款；仅 CREATED/WAITING_PAYMENT/WAITING_MATCH/PARTIAL_MATCHED 可取消 |
| GET | `/api/v1/orders/{order_id}/match` | 撮合详情：目标/已撮合/剩余金额 + 撮合明细 |

订单字段（响应均为金额字符串）：`order_no, order_type, product_name, quantity, total_amount, service_fee, payable_amount, matched_amount, status, ...`

---

## 7. 预约 `reservations`（均需用户 token）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/reservations` | 为订单创建预约 `{order_id}`（同一订单不重复创建） |
| GET | `/api/v1/reservations` | 我的预约分页 |
| GET | `/api/v1/reservations/matching/status/{order_id}` | 撮合状态摘要（目标/已撮合/剩余 + match_count） |

---

## 8. 账户 `accounts`（均需用户 token）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/accounts` | 我的账户 `{account_no, available_amount, frozen_amount, pending_amount}` |
| GET | `/api/v1/accounts/transactions` | 资金流水分页（可选 `business_type` 过滤） |

---

## 9. 财务 `finance`

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/v1/withdrawals` | 用户 | 提现申请 `{amount, bank_name, bank_account, account_name}`。要求实名 APPROVED 且无高风控；立即冻结余额 |
| GET | `/api/v1/withdrawals` | 用户 | 我的提现记录分页（可选 `status`） |
| GET | `/api/v1/fees` | 公开 | 启用中的费率规则 |
| GET | `/api/v1/promotion/records` | 用户 | 我的推广奖励记录分页 |

---

## 10. 客服 / 申诉 / 通知 `support`

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/v1/support/tickets` | 用户 | 创建工单 `{category, title, content, order_id?, priority?}` |
| GET | `/api/v1/support/tickets` | 用户 | 我的工单分页（可选 `status`） |
| GET | `/api/v1/support/tickets/{ticket_id}` | 用户 | 工单详情（含消息列表，仅本人可见） |
| POST | `/api/v1/support/tickets/{ticket_id}/messages` | 用户 | 回复工单 `{content, attachments?}` |
| POST | `/api/v1/appeals` | 用户 | 提交申诉 `{subject, content, order_id?, evidence?}` |
| GET | `/api/v1/appeals` | 用户 | 我的申诉分页（可选 `status`） |
| GET | `/api/v1/notifications` | 用户 | 我的通知分页（含 `unread` 未读数） |
| POST | `/api/v1/notifications/{notification_id}/read` | 用户 | 标记单条已读 |
| POST | `/api/v1/notifications/read-all` | 用户 | 全部标记已读，返回 `{count}` |
| GET | `/api/v1/announcements` | 公开 | 启用中的公告列表 |

---

## 11. 管理后台 `admin`

管理员 token 通过 `POST /api/v1/admin/login` 获取（`{"username", "password"}`，返回 `access_token` + `admin` + `permissions`）。除 `login` 外，**所有后台接口均要求管理员 Bearer token**（匿名访问一律 401/403，见回归测试 `test_admin_endpoints_require_auth`）。

### 11.1 认证与 Dashboard

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/admin/login` | 公开：管理员登录 |
| GET | `/api/v1/admin/me` | 当前管理员信息 + 权限码列表 |
| GET | `/api/v1/admin/dashboard` | 统计概览：用户/订单总量与今日、活跃用户、待撮合、异常订单、待处理申诉/提现、服务费总额、近 7 天趋势图表 |

### 11.2 用户管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/users` | 用户分页（可选 user_id/phone/status/realname_status/risk_level） |
| GET | `/api/v1/admin/users/{user_id}` | 用户详情（含账户、实名、会员） |
| POST | `/api/v1/admin/users/{user_id}/freeze` | 冻结用户（需 `role_code=SUPER_ADMIN` 或 `is_super`），`{reason}` |
| POST | `/api/v1/admin/users/{user_id}/unfreeze` | 解冻用户 |
| POST | `/api/v1/admin/users/{user_id}/adjust` | 人工调账 `{amount, reason}`（正数为入账，负数为出账；必须填原因；写操作日志） |
| POST | `/api/v1/admin/realname/{ver_id}/review` | 实名审核 `{approve, reason}`，通过后同步 `users.realname_status` |

### 11.3 订单与撮合

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/orders` | 订单分页（可选 order_no/status/order_type/user_id） |
| GET | `/api/v1/admin/orders/{order_id}` | 订单详情（含状态日志与撮合明细） |
| POST | `/api/v1/admin/orders/{order_id}/manual-match` | 人工撮合（写 match_logs 与操作日志），返回 `{matched}` |
| GET | `/api/v1/admin/matching` | 撮合中订单（WAITING_MATCH / PARTIAL_MATCHED / FULL_MATCHED） |
| GET | `/api/v1/admin/matching/jobs` | 撮合扫描任务记录分页 |

### 11.4 财务

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/accounts/{user_id}` | 指定用户账户 |
| GET | `/api/v1/admin/transactions` | 全量流水分页（可选 user_id/business_type） |
| GET | `/api/v1/admin/withdrawals` | 提现单分页（可选 status） |
| POST | `/api/v1/admin/withdrawals/{withdrawal_id}/review` | 审核 `{approve, reason}`（驳回自动解冻退款） |
| POST | `/api/v1/admin/withdrawals/{withdrawal_id}/complete` | 提现完成（冻结正式出账） |
| GET | `/api/v1/admin/fees` | 费率规则列表 |
| PUT | `/api/v1/admin/fees/{fee_type}` | 更新费率 `{rate, min_fee, max_fee, name?, status?}`（写操作日志） |
| GET | `/api/v1/admin/fees/records` | 费用记录分页 |
| GET | `/api/v1/admin/promotions` | 推广奖励记录分页 |

### 11.5 风控

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/risk/events` | 风险事件分页（可选 status） |
| POST | `/api/v1/admin/risk/events/{event_id}/review` | 处理事件 `{approve, action?, reason?}`：通过则执行动作（FREEZE/BLOCK），否则 DISMISSED |

### 11.6 客服与申诉

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/tickets` | 工单分页（可选 status） |
| POST | `/api/v1/admin/tickets/{ticket_id}/reply` | 客服回复 `{content, attachments?}` |
| POST | `/api/v1/admin/tickets/{ticket_id}/close` | 关闭工单 |
| GET | `/api/v1/admin/appeals` | 申诉分页（可选 status） |
| POST | `/api/v1/admin/appeals/{appeal_id}/process` | 处理申诉 `{approve, result}` |

### 11.7 RBAC 管理员与角色

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/admins` | 管理员列表 |
| POST | `/api/v1/admin/admins` | 创建管理员 `{username, password, nickname?, role_code?, role_ids?}` |
| PUT | `/api/v1/admin/admins/{admin_id}` | 更新管理员（昵称/密码/状态/角色） |
| GET | `/api/v1/admin/roles` | 角色列表（含权限码） |
| POST | `/api/v1/admin/roles` | 创建角色 `{code, name, description?, permission_codes}` |
| PUT | `/api/v1/admin/roles/{role_id}` | 更新角色 |
| GET | `/api/v1/admin/permissions` | 全部权限点列表（按分组排序） |

### 11.8 日志 / 邀请码 / 公告

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/logs` | 操作日志分页（含操作者/IP/requestId） |
| POST | `/api/v1/admin/invites` | 生成系统邀请码 `{count, expires_in_days?}`（creator_id=0） |
| GET | `/api/v1/admin/announcements` | 公告列表 |
| POST | `/api/v1/admin/announcements` | 发布公告 `{title, content?, type?}` |

---

## 12. 其他

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查（Docker 部署经 Nginx `http://localhost/health` 访问） |
| GET | `/api/docs`（FastAPI 默认 `/docs`） | Swagger UI（仅后端容器/本地开发可直接访问 `http://localhost:8000/docs`；Nginx 默认仅代理 `/api/` 路径，如需对外请补充 location，见 DEPLOYMENT.md） |
