# 测试

## 1. 测试栈

| 组件 | 说明 |
| --- | --- |
| pytest | 测试框架，`pyproject.toml` 配置 `asyncio_mode=auto`（pytest-asyncio），测试无需手动 `asyncio.run` |
| httpx + TestClient | FastAPI/Starlette 内置 `TestClient` 驱动异步接口测试 |
| SQLite（aiosqlite） | 测试数据库（内存式临时库，由 `tests/conftest.py` 注入环境变量，不触碰 MySQL） |
| MemoryRedis | 进程内 Redis 兜底（`REDIS_HOST=""`），锁/限流/验证码语义与 Redis 一致 |

## 2. 快速运行

```bash
cd backend

# 运行全部测试（推荐；conftest 自动注入 PYTHONPATH 与测试环境变量）
python -m pytest -v

# 只跑某个目录 / 文件
python -m pytest tests/api/ -v
python -m pytest tests/matching/test_concurrency.py -v

# 只跑某个用例（-k 按关键字）
python -m pytest -k "concurrent or overflow" -v

# 输出覆盖率（需先安装 pytest-cov）
python -m pytest --cov=app --cov-report=term-missing
```

测试环境自动约定（见 `tests/conftest.py`）：`APP_ENV=test`、`SQLITE_PATH` 指向临时文件、`MYSQL_HOST=""`、`REDIS_HOST=""`、`MATCH_SCAN_INTERVAL=60`。conftest 在测试会话开始时执行建表（`init_db`/`create_all`）并注入种子管理员账号。

## 3. 测试目录结构

```text
tests/
├── conftest.py                    # 全局 fixtures：client / db / admin_token / user_token / test_accounts
├── unit/                          # 单元测试
│   ├── test_security.py           # JWT 签发/校验/过期/类型错误；Argon2 哈希与密码强度
│   ├── test_invite.py             # 邀请码生成/核销/禁用/过期
│   ├── test_fee.py                # 服务费计算、费率快照、限额与异常费率
│   └── test_admin_api.py          # 后台接口鉴权回归（无 token 一律 401）
├── integration/                   # 集成测试
│   ├── test_auth_flow.py          # 注册→登录→刷新→鉴权完整链路
│   ├── test_account.py            # 开户、入账/出账/冻结、余额不足
│   └── test_withdrawal.py         # 提现申请→审核→完成 全流程
├── matching/                      # 撮合与并发专项
│   ├── test_order_matching.py     # 撮合正确性：A→多B、全额/部分、结算、费用与推广
│   └── test_concurrency.py        # 并发防超卖/防重复/乐观锁
└── api/                           # API 级测试
    └── test_support.py            # 工单与通知
```

## 4. 当前结果

| 检查 | 结果 |
| --- | --- |
| 单元测试 | 通过 |
| 集成测试 | 通过 |
| 撮合/并发测试 | 通过（防超卖、幂等、乐观锁冲突） |
| API 级测试 | 通过 |
| **合计用例数** | **35** |
| 静态检查 `ruff` | 0 条错误（E,F,W,I,UP,B,ASYNC） |
| 类型检查 `mypy` | 0 条错误（`mypy app`，`pydantic.mypy` 插件，exclude `alembic`） |

```text
python -m pytest
  ============================= test session starts ==============================
  collected 35 items
  35 passed in ~2s
```

## 5. 重点覆盖场景

### 5.1 并发与防超卖（`tests/matching/test_concurrency.py`）

- 多线程并发支付/撮合同一订单：最终 `SUM(match_amount) <= total_amount`，不出现负余额。
- 同一买卖对重复撮合：`match_orders` 幂等判重，不产生重复撮合记录。
- 并发余额操作：`accounts.version` 乐观锁冲突时回滚并返回错误，账实一致。

### 5.2 撮合正确性（`tests/matching/test_order_matching.py`）

- A 订单金额由多个 B 订单共同满足（A→多B），撮合金额精确到分。
- 全额撮合 → 结算：买方冻结→卖方可用，平台服务费入账，`fee_records` 记录费率快照。
- 推广奖励仅对 `BUY/SERVICE` 且已完成的真实成交发放，`PENDING → SETTLED` 并关联流水。

### 5.3 幂等与防重

- `POST /orders` 携带 `Idempotency-Key`：重复请求返回首次结果，不产生第二笔订单。
- 支付/取消状态机非法流转返回 `ORDER_INVALID_STATUS`。

### 5.4 鉴权回归（`tests/unit/test_admin_api.py`）

- 遍历全部后台 GET 端点，无 Bearer token 一律 401；有用户 token（非管理员）访问后台一律 403。
- 该用例防止后续新增后台 GET 端点时遗漏鉴权（历史问题：GET 端点曾被遗漏鉴权，已修复并由本测试固化）。

### 5.5 账户与提现（`tests/integration/test_withdrawal.py`）

- 未实名 / 风控 HIGH 提现被拦截（`RISK_REVIEW_REQUIRED`）。
- 余额不足提现失败；申请成功即冻结。
- 审核驳回 → 自动解冻退款；审核通过 → 完成 → 冻结正式出账，流水方向正确。

### 5.6 认证链路（`tests/integration/test_auth_flow.py`）

- 注册（验证码校验、邀请码核销、自动开户）→ 登录 → 刷新 → 携带 access 访问受保护接口 → 过期返回 `TOKEN_EXPIRED`。

## 6. 后续建议

- 引入 `pytest-cov` 并设定覆盖率门禁（当前未强制）。
- 增加 MySQL 真实集成测试（测试环境可挂 `MYSQL_HOST` 验证行锁/FOR UPDATE 语义）。
- 增加真实 Redis 下的分布式锁并发测试（当前用 MemoryRedis，锁语义一致但非跨进程）。
- 为撮合引擎补充随机模糊测试（随机订单量/金额/状态组合下的不变量校验）。
