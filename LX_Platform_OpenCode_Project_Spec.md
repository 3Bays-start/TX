# LX Platform — 订单撮合与会员服务平台

## 开发级项目规格 / PRD / Technical Specification

**版本：V1.0**  
**后端：Python 3.12 + FastAPI**  
**前端：Vue 3 + TypeScript**  
**管理后台：Vue 3 + Element Plus**  
**数据库：MySQL 8**  
**缓存：Redis**  
**消息队列：RabbitMQ**  
**任务：Celery + Celery Beat**  
**部署：Docker + Nginx**  
**第一阶段：不接入 USDT 支付 API**

> **合规边界：** 本项目按真实商品/服务订单撮合平台设计。不得实现以新用户资金支付旧用户收益、固定层级资金返佣、虚构投资收益、人为设置递增且不可逆提现门槛等机制。平台收入应来自真实、可披露的商品/服务费用。推广奖励必须与真实商品/服务成交绑定，并支持退款/取消时冲销。

---

# 1. 项目定位

LX Platform 是一个：

- 邀请码注册
- 会员体系
- 商品/服务
- 订单管理
- 预约队列
- A 订单 → 多 B 订单撮合
- 平台服务费
- 合规推广奖励
- 提现
- 客服/申诉
- 风控
- 管理后台
- RBAC 权限
- 完整账务流水
- 审计日志

组成的前后端分离平台。

核心流程：

```text
邀请码
  ↓
注册
  ↓
实名认证
  ↓
会员/服务资格
  ↓
创建订单
  ↓
预约
  ↓
进入撮合队列
  ↓
Matching Engine
  ↓
A订单
  ├── B1
  ├── B2
  └── B3
  ↓
达到订单需求
  ↓
订单完成
  ↓
产生平台服务费
```

# 2. 技术栈

## 用户端

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Vant
- Axios

## 管理后台

- Vue 3
- TypeScript
- Vite
- Pinia
- Element Plus
- ECharts
- Axios

## 后端

- Python 3.12
- FastAPI
- SQLAlchemy 2.0
- Pydantic 2
- Alembic
- asyncmy

## 基础设施

- MySQL 8
- Redis
- RabbitMQ
- Celery
- Celery Beat
- Nginx
- Docker
- Docker Compose

## 安全/质量

- JWT
- Argon2id
- RBAC
- Rate Limit
- Pytest
- pytest-asyncio
- Ruff
- Mypy

# 3. 总体架构

```text
                    ┌─────────────────┐
                    │    Vue3 用户端   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │      Nginx      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ FastAPI Backend │
                    │   Python 3.12   │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐    ┌──────▼──────┐    ┌─────▼──────┐
   │   MySQL 8   │    │    Redis    │    │  RabbitMQ  │
   └─────────────┘    └─────────────┘    └─────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │Celery Worker│
                                        └──────┬──────┘
                                               │
                              ┌────────────────┼────────────────┐
                              ↓                ↓                ↓
                             撮合             风控             通知
```

# 4. 系统角色

```text
SUPER_ADMIN
ADMIN
CUSTOMER_SERVICE
FINANCE
RISK
USER
```

## SUPER_ADMIN

拥有全部权限：

- 用户管理
- 管理员管理
- 角色权限
- 订单管理
- 撮合管理
- 财务管理
- 提现审核
- 风控
- 客服
- 商品
- 会员
- 系统配置
- 操作日志

## ADMIN

通过 RBAC 分配权限，例如：

```text
user:view
user:freeze
order:view
order:operate
order:match
ticket:view
ticket:reply
```

## CUSTOMER_SERVICE

```text
user:view
order:view
ticket:view
ticket:reply
ticket:assign
ticket:close
appeal:view
appeal:process
```

## FINANCE

```text
account:view
transaction:view
withdrawal:view
withdrawal:review
fee:view
```

## RISK

```text
risk:view
risk:review
risk:freeze
risk:release
```

# 5. 用户注册

必须通过邀请码注册：

```text
手机号
 ↓
短信验证码
 ↓
邀请码
 ↓
邀请码校验
 ↓
密码
 ↓
创建用户
 ↓
绑定上级关系
```

邀请码状态：

```text
UNUSED
USED
DISABLED
EXPIRED
```

# 6. 邀请码模块

表：

```text
invite_codes
```

字段：

```text
id
code
creator_id
status
used_by
used_at
expires_at
created_at
```

要求：

- code 唯一
- 默认一次性使用
- 可设置有效期
- 可禁用
- 使用后不可再次使用
- 记录创建者
- 记录使用者

# 7. 用户关系树

示例：

```text
A
├── B
│   ├── D
│   └── E
└── C
```

表：

```text
user_relations
```

字段：

```text
user_id
parent_id
level
path
created_at
```

支持：

- 直属下级
- 团队人数
- 活跃人数
- 团队订单统计
- 推广统计

# 8. 用户模块

表：

```text
users
user_profiles
user_devices
user_login_logs
```

用户状态：

```text
ACTIVE
FROZEN
DISABLED
PENDING_REVIEW
```

个人中心：

- 用户资料
- 实名认证状态
- 会员等级
- 订单
- 账户
- 流水
- 团队
- 消息
- 安全设置

# 9. 实名认证

字段：

```text
name
id_number
document_front
document_back
status
review_reason
reviewed_by
reviewed_at
```

状态：

```text
PENDING
APPROVED
REJECTED
```

敏感信息必须：

- 加密保存
- 后台脱敏展示
- 最小权限访问
- 全程审计

# 10. 会员模块

表：

```text
membership_levels
memberships
membership_orders
```

会员等级：

```text
普通会员
高级会员
VIP
```

每级配置：

```text
name
price
duration
benefits
order_limits
service_permissions
status
```

# 11. 商品/服务模块

表：

```text
product_categories
products
product_skus
```

商品字段：

```text
product_id
product_no
name
description
price
status
created_at
updated_at
```

支持：

- 分类
- SKU
- 价格
- 上下架
- 排序
- 详情
- 服务说明

# 12. 订单模块

订单类型：

```text
BUY
SELL
SERVICE
```

订单表：

```text
orders
order_items
order_status_logs
buy_orders
sell_orders
```

核心字段：

```text
id
order_no
user_id
order_type
product_id
total_amount
service_fee
payable_amount
status
reservation_time
created_at
updated_at
```

# 13. 订单状态机

正常：

```text
CREATED
 ↓
WAITING_PAYMENT
 ↓
PAID
 ↓
WAITING_MATCH
 ↓
PARTIAL_MATCHED
 ↓
FULL_MATCHED
 ↓
PROCESSING
 ↓
COMPLETED
```

异常：

```text
CANCELLED
EXPIRED
DISPUTED
RISK_REVIEW
```

要求：

- 前端不得直接修改 status
- 所有状态变更由后端状态机控制
- 每次状态变化写入 `order_status_logs`
- 非法状态转换必须拒绝

# 14. 预约模块

表：

```text
reservation_orders
```

字段：

```text
id
reservation_no
order_id
user_id
reserved_at
priority
status
created_at
```

排序规则：

```text
风险状态
 ↓
商品/服务
 ↓
预约时间
 ↓
订单创建时间
```

最早有效预约优先。

# 15. 核心撮合模块

一个 A 订单可以匹配多个 B 订单。

例如：

```text
A = 10000

B1 = 2000
B2 = 3000
B3 = 5000
```

最终：

```text
A
├── B1 2000
├── B2 3000
└── B3 5000

总计 = 10000
```

表：

```text
match_orders
match_logs
matching_jobs
```

字段：

```text
match_no
parent_order_id
buyer_order_id
seller_order_id
match_amount
status
created_at
completed_at
```

# 16. 撮合算法

伪代码：

```python
def match_order(order_id):
    order = lock_order(order_id)

    remaining = order.total_amount - order.matched_amount

    if remaining <= 0:
        return

    candidates = find_candidates(order)

    for candidate in candidates:
        if remaining <= 0:
            break

        available = get_available_amount(candidate)

        match_amount = min(
            available,
            remaining
        )

        if match_amount <= 0:
            continue

        create_match(
            order=order,
            candidate=candidate,
            amount=match_amount
        )

        remaining -= match_amount

    if remaining == 0:
        complete_matching(order)
```

必须保证：

```text
SUM(match_amount) <= order.total_amount
```

# 17. 撮合并发安全

必须同时使用：

```text
Redis Distributed Lock
+
MySQL SELECT ... FOR UPDATE
+
Database Transaction
+
Idempotency
+
Optimistic Lock
```

锁：

```text
lock:matching:order:{order_id}
```

数据库行锁：

```sql
SELECT *
FROM orders
WHERE id = ?
FOR UPDATE;
```

绝对禁止多个 Worker 无锁修改同一订单。

# 18. 24 小时扫描任务

使用：

```text
Celery Beat
+
Celery Worker
```

每天执行：

```text
扫描 WAITING_MATCH
 ↓
检查预约时间
 ↓
检查订单状态
 ↓
检查用户状态
 ↓
检查风险状态
 ↓
执行撮合
 ↓
写任务日志
```

任务：

```python
@celery_app.task
def scan_pending_orders():
    ...
```

任务表：

```text
matching_jobs
```

字段：

```text
job_id
start_time
end_time
processed_count
success_count
failed_count
error_message
status
```

# 19. 实时撮合

订单进入：

```text
WAITING_MATCH
```

后立即尝试。

如果无法匹配：

```text
进入待匹配队列
```

Celery Beat 每24小时重新扫描。

# 20. 平台服务费

服务费必须来自真实商品/服务订单。

配置表：

```text
fee_rules
```

字段：

```text
fee_type
rate
min_fee
max_fee
status
effective_at
```

示例：

```text
订单金额：10000
服务费率：5%

服务费：500
```

公式：

```text
service_fee = order_amount × fee_rate
```

历史订单必须保存当时的：

```text
rate
base_amount
fee_amount
```

后台修改费率不得影响历史订单。

# 21. 账户系统

表：

```text
accounts
account_transactions
```

账户字段：

```text
available_amount
frozen_amount
pending_amount
version
```

任何余额变化必须写流水。

# 22. 账务事务

禁止：

```python
account.balance += amount
```

而不产生流水。

标准流程：

```text
BEGIN
 ↓
锁账户
 ↓
读取余额
 ↓
验证
 ↓
计算
 ↓
写 account_transactions
 ↓
更新 accounts
 ↓
COMMIT
```

金额统一：

```python
from decimal import Decimal
```

禁止使用 `float` 处理资金。

# 23. 账务流水

字段：

```text
transaction_no
user_id
account_id
business_type
business_id
amount
before_balance
after_balance
direction
created_at
```

业务类型：

```text
ORDER_PAYMENT
ORDER_SETTLEMENT
SERVICE_FEE
REFUND
WITHDRAWAL
ADJUSTMENT
PROMOTION_REWARD
```

人工调整必须：

- 记录管理员
- 记录原因
- 记录前后余额
- 记录业务单号
- 写入审计日志

# 24. 提现模块

表：

```text
withdrawal_orders
withdrawal_logs
```

流程：

```text
用户申请
 ↓
参数校验
 ↓
余额冻结
 ↓
风控
 ↓
人工/自动审核
 ↓
处理
 ↓
完成
```

状态：

```text
PENDING
REVIEWING
APPROVED
PROCESSING
COMPLETED
REJECTED
```

限制：

```text
实名认证
单笔限额
日限额
风控审核
结算周期
```

不得设置人为递增且不可逆的提现门槛。

# 25. 推广体系

推广关系：

```text
A
├── B
└── C
```

推广奖励必须与真实商品/服务成交绑定。

表：

```text
promotion_rules
promotion_records
```

字段：

```text
source_user_id
source_order_id
beneficiary_user_id
reward_amount
status
created_at
```

退款时：

```text
订单退款
 ↓
推广奖励冲销
```

不得单纯以发展下线数量作为资金收益依据。

# 26. 客服

表：

```text
support_tickets
ticket_messages
```

状态：

```text
OPEN
PROCESSING
WAITING_USER
RESOLVED
CLOSED
```

功能：

- 创建工单
- 上传附件
- 客服回复
- 分配客服
- 优先级
- 关联订单
- 关闭工单

# 27. 申诉

表：

```text
appeals
appeal_logs
```

流程：

```text
用户提交
 ↓
上传证据
 ↓
客服/管理员审核
 ↓
处理
 ↓
记录结果
```

所有处理必须审计。

# 28. 风控

表：

```text
risk_rules
risk_events
risk_users
```

风险来源：

```text
异常登录
设备异常
IP异常
订单频率异常
短时间大量取消
异常提现
异常关联账户
重复申诉
```

等级：

```text
LOW
MEDIUM
HIGH
CRITICAL
```

动作：

```text
ALLOW
VERIFY
REVIEW
FREEZE
BLOCK
```

# 29. 通知

表：

```text
notifications
announcements
```

通知类型：

```text
ORDER
MATCH
PAYMENT
WITHDRAWAL
TICKET
SYSTEM
RISK
```

支持：

- 未读
- 已读
- 全部已读
- 系统公告

# 30. 后台 Dashboard

显示：

```text
用户总数
今日新增
活跃用户
订单总数
今日订单
待匹配
匹配中
异常订单
申诉
提现待审核
平台服务收入
```

图表：

```text
用户增长
订单趋势
撮合成功率
服务费收入
提现趋势
风险事件
```

# 31. 后台用户管理

筛选：

```text
用户ID
手机号
状态
会员等级
注册时间
实名认证
风险等级
```

操作：

```text
查看
冻结
解冻
禁用
查看订单
查看流水
查看团队
查看登录记录
查看操作日志
```

# 32. 后台订单管理

筛选：

```text
订单号
用户
订单状态
订单类型
金额
时间
```

订单详情：

```text
订单信息
用户信息
预约信息
撮合记录
费用
状态历史
申诉
操作日志
```

# 33. 后台撮合管理

页面：

```text
待匹配
匹配中
已匹配
异常
```

详情：

```text
A订单
目标金额
已匹配金额
剩余金额

B订单列表
匹配金额
状态
预约时间
```

管理员人工操作必须有：

```text
操作原因
操作人
操作时间
IP
request_id
```

# 34. RBAC

表：

```text
admin_users
admin_roles
admin_permissions
admin_user_roles
admin_role_permissions
```

示例：

```text
SUPER_ADMIN
ADMIN_ORDER
ADMIN_FINANCE
ADMIN_CUSTOMER_SERVICE
ADMIN_RISK
```

接口：

```python
@router.post(
    "/users/{user_id}/freeze",
    dependencies=[
        Depends(require_permission("user:freeze"))
    ]
)
```

# 35. API 结构

```text
/api/v1/auth
/api/v1/users
/api/v1/invites
/api/v1/memberships
/api/v1/products
/api/v1/orders
/api/v1/reservations
/api/v1/matching
/api/v1/accounts
/api/v1/fees
/api/v1/promotion
/api/v1/withdrawals
/api/v1/support
/api/v1/appeals
/api/v1/risk
/api/v1/notifications
/api/v1/admin
```

# 36. 核心 API

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh

GET  /api/v1/users/me
GET  /api/v1/users/team

POST /api/v1/orders
GET  /api/v1/orders
GET  /api/v1/orders/{order_id}

POST /api/v1/reservations
GET  /api/v1/reservations

GET  /api/v1/accounts
GET  /api/v1/accounts/transactions

POST /api/v1/withdrawals
GET  /api/v1/withdrawals

POST /api/v1/support/tickets
GET  /api/v1/support/tickets

POST /api/v1/appeals
```

# 37. 后台 API

```text
/api/v1/admin/users
/api/v1/admin/orders
/api/v1/admin/matching
/api/v1/admin/accounts
/api/v1/admin/withdrawals
/api/v1/admin/fees
/api/v1/admin/promotions
/api/v1/admin/risk
/api/v1/admin/tickets
/api/v1/admin/appeals
/api/v1/admin/admins
/api/v1/admin/roles
/api/v1/admin/permissions
/api/v1/admin/logs
```

# 38. 统一响应

成功：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "requestId": "req_xxxxx"
}
```

失败：

```json
{
  "code": "ORDER_INVALID_STATUS",
  "message": "当前订单状态不允许执行此操作",
  "data": null,
  "requestId": "req_xxxxx"
}
```

# 39. 错误码

```text
AUTH_INVALID
TOKEN_EXPIRED
PERMISSION_DENIED

USER_NOT_FOUND
USER_FROZEN
USER_DISABLED

INVITE_CODE_INVALID
INVITE_CODE_USED
INVITE_CODE_EXPIRED

ORDER_NOT_FOUND
ORDER_INVALID_STATUS
ORDER_ALREADY_COMPLETED

MATCH_NOT_FOUND
MATCH_AMOUNT_INVALID
MATCH_OVERFLOW

ACCOUNT_NOT_FOUND
INSUFFICIENT_BALANCE

WITHDRAWAL_INVALID
WITHDRAWAL_LIMIT_EXCEEDED

RISK_REVIEW_REQUIRED
```

# 40. 幂等

以下接口必须幂等：

```text
创建订单
创建提现
确认订单
提交申诉
账户入账
订单完成
退款
```

客户端：

```text
Idempotency-Key
```

服务端：

```text
idempotency_records
```

相同 Key 只能成功一次。

# 41. JWT

认证：

```text
Access Token
+
Refresh Token
```

密码：

```text
Argon2id
```

禁止保存明文密码。

# 42. Redis

用途：

```text
验证码
登录限制
接口限流
分布式锁
缓存
幂等
撮合队列
```

示例：

```text
lock:matching:order:{order_id}
```

# 43. RabbitMQ + Celery

事件：

```text
order.created
order.paid
order.matched
order.completed

withdrawal.created
risk.triggered

ticket.created
notification.created
```

任务：

```text
matching_tasks.py
order_tasks.py
risk_tasks.py
notification_tasks.py
```

# 44. 文件上传

支持：

```text
订单凭证
实名认证材料
申诉材料
```

要求：

```text
限制扩展名
限制 MIME
限制文件大小
随机文件名
病毒扫描
私有存储
临时访问 URL
```

# 45. 安全

必须防护：

```text
SQL Injection
XSS
CSRF
IDOR
暴力破解
接口刷量
重复提交
越权访问
订单篡改
金额篡改
并发超额撮合
```

安全原则：

```text
前端不可信
所有金额后端计算
所有状态后端控制
所有权限后端验证
所有资金变化必须事务化
```

# 46. 日志

日志分：

```text
Application Log
Access Log
Security Log
Business Log
Audit Log
```

必须包含：

```text
request_id
user_id
admin_id
ip
user_agent
timestamp
```

# 47. 审计日志

表：

```text
operation_logs
```

字段：

```text
id
operator_type
operator_id
action
module
target_type
target_id
before_data
after_data
reason
ip
user_agent
request_id
created_at
```

敏感操作必须写日志：

```text
冻结用户
解冻用户
修改订单
人工撮合
人工调整账务
提现审核
修改费率
修改权限
修改系统配置
```

# 48. 数据库设计总表

```text
users
user_profiles
user_devices
user_login_logs

invite_codes
user_relations

realname_verifications

membership_levels
memberships
membership_orders

product_categories
products
product_skus

orders
order_items
order_status_logs
buy_orders
sell_orders

reservation_orders

match_orders
match_logs
matching_jobs

accounts
account_transactions

fee_rules
fee_records

promotion_rules
promotion_records

withdrawal_orders
withdrawal_logs

support_tickets
ticket_messages

appeals
appeal_logs

risk_rules
risk_events
risk_users

admin_users
admin_roles
admin_permissions
admin_user_roles
admin_role_permissions

notifications
announcements
operation_logs
idempotency_records
system_configs
```

# 49. 后端目录

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   │
│   ├── core/
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   ├── response.py
│   │   ├── permissions.py
│   │   └── logging.py
│   │
│   ├── models/
│   ├── schemas/
│   ├── api/
│   │   └── v1/
│   ├── services/
│   ├── repositories/
│   ├── tasks/
│   └── utils/
│
├── alembic/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── matching/
│   ├── account/
│   └── security/
│
├── requirements.txt
├── pyproject.toml
├── Dockerfile
└── .env.example
```

# 50. 前端页面

用户端：

```text
/login
/register
/home
/membership
/products
/products/:id
/reservation
/orders
/orders/:id
/orders/:id/match
/team
/account
/account/transactions
/withdraw
/notifications
/profile
/security
/customer-service
/appeal
```

后台：

```text
/admin/login
/admin/dashboard
/admin/users
/admin/users/:id
/admin/orders
/admin/orders/:id
/admin/matching
/admin/matching/:id
/admin/products
/admin/memberships
/admin/accounts
/admin/transactions
/admin/fees
/admin/promotions
/admin/withdrawals
/admin/tickets
/admin/appeals
/admin/risk
/admin/admins
/admin/roles
/admin/permissions
/admin/announcements
/admin/logs
/admin/settings
```

# 51. Docker

服务：

```text
nginx
backend
celery-worker
celery-beat
mysql
redis
rabbitmq
web
admin
```

启动：

```bash
docker compose up -d
```

# 52. Docker 网络

数据库、Redis、RabbitMQ 不允许直接暴露公网。

```text
Internet
 ↓
Nginx
 ↓
Backend
 ↓
Internal Network
 ├── MySQL
 ├── Redis
 └── RabbitMQ
```

# 53. 环境变量

`.env.example`：

```env
APP_ENV=production
APP_NAME=lx-platform

MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=lx_platform
MYSQL_USER=lx_app
MYSQL_PASSWORD=CHANGE_ME

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=CHANGE_ME

RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=lx
RABBITMQ_PASSWORD=CHANGE_ME

JWT_SECRET=CHANGE_ME
JWT_ACCESS_EXPIRE=7200
JWT_REFRESH_EXPIRE=2592000

UPLOAD_MAX_SIZE=10485760
```

任何真实密码、JWT Secret、API Key 都不得提交 Git。

# 54. 测试要求

## 单元测试

```text
费用计算
订单状态
撮合金额
提现限制
邀请码
推广奖励
权限
```

## 集成测试

```text
注册 → 登录
创建订单 → 预约
订单 → 撮合
订单 → 完成
账户 → 流水
提现 → 审核
```

## 并发测试

```text
100 个 Worker
同时处理一个订单
```

必须保证：

```text
不超额
不重复
不产生负余额
```

# 55. 核心验收

```text
[ ] 邀请码注册
[ ] 登录
[ ] JWT
[ ] RBAC
[ ] 实名
[ ] 会员
[ ] 商品
[ ] 订单
[ ] 预约
[ ] A→多B撮合
[ ] 24小时扫描
[ ] 服务费
[ ] 账户
[ ] 流水
[ ] 提现
[ ] 团队
[ ] 客服
[ ] 申诉
[ ] 风控
[ ] 后台
[ ] 超级管理员
[ ] 管理员
[ ] 审计日志
[ ] Docker
[ ] HTTPS
[ ] 数据备份
[ ] 自动测试
```

# 56. 开发顺序

```text
Phase 1  项目初始化
Phase 2  数据库
Phase 3  认证 + 邀请码
Phase 4  用户
Phase 5  实名
Phase 6  会员
Phase 7  商品/服务
Phase 8  订单
Phase 9  预约
Phase 10 撮合
Phase 11 账户/账务
Phase 12 服务费
Phase 13 提现
Phase 14 推广
Phase 15 客服/申诉
Phase 16 风控
Phase 17 管理后台
Phase 18 前端完善
Phase 19 测试
Phase 20 Docker/部署
Phase 21 安全审计
```

每个 Phase 完成后：

```bash
ruff check .
mypy .
pytest
```

并检查：

```text
数据库 Migration
API
权限
异常
幂等
事务
安全
```

# 57. OpenCode / Codex 开工总指令

你现在是 LX Platform 的主程开发 Agent。

严格按照本文件实现项目。

## 开发原则

1. 不一次性生成全部代码。
2. 按 Phase 顺序开发。
3. 每个 Phase 必须可运行。
4. 每个 Phase 必须有测试。
5. 不允许用 Mock 代替核心业务。
6. 不允许 TODO 代替核心业务。
7. 不允许删除测试来规避失败。
8. 不允许忽略异常。
9. 不允许使用 float 处理金额。
10. 不允许前端直接控制订单状态。
11. 不允许绕过 RBAC。
12. 不允许明文保存密码。
13. 不允许把密钥写入代码。
14. 不允许将 MySQL/Redis/RabbitMQ 暴露到公网。
15. 不允许无事务修改账户余额。
16. 不允许无锁并发修改同一订单。
17. 不允许撮合金额超过订单剩余金额。
18. 不允许重复处理同一个业务请求。

## 每完成一个 Phase

执行：

```bash
ruff check .
mypy .
pytest
```

输出：

```text
Phase
完成内容
新增文件
修改文件
数据库 Migration
新增 API
新增测试
测试结果
已知问题
下一阶段
```

## 最终必须生成

```text
README.md
ARCHITECTURE.md
DATABASE.md
API.md
SECURITY.md
DEPLOYMENT.md
TESTING.md
CHANGELOG.md
```

最终必须可以：

```bash
docker compose up -d
```

启动：

```text
Nginx
FastAPI
Celery Worker
Celery Beat
MySQL
Redis
RabbitMQ
Web
Admin
```

最终输出：

```text
项目目录
启动方式
数据库初始化
管理员初始化
API 文档地址
用户端地址
后台地址
测试结果
Docker 状态
数据库 Migration 状态
安全检查结果
未解决问题
```

**现在从 Phase 1 开始，不要跳过阶段。**
