# LX Platform — 订单撮合与会员服务平台

LX Platform 是一个前后端分离的订单撮合与会员服务平台：用户通过邀请码注册，完成实名认证后可购买会员/商品服务、创建订单（买入 / 卖出 / 服务）、预约排队，由撮合引擎将「A 订单 → 多 B 订单」自动撮合并结算资金；平台按成交收取服务费，并为真实成交提供合规推广奖励。内置完整的账户账务（可用 / 冻结 / 待结算 + 流水）、提现审核、客服工单、申诉、风控事件与后台 RBAC 权限体系。

> 合规边界：本平台按真实商品/服务订单撮合平台设计。推广奖励必须与真实商品/服务成交绑定，退款/取消时自动冲销；不存在资金池、固定层级返佣与虚构收益。平台收入来自真实、可披露的商品/服务费用。

## 功能清单

| 模块 | 功能 |
| --- | --- |
| 认证 | 邀请码注册、短信验证码（开发环境直接返回）、密码登录、JWT 刷新、修改密码 |
| 用户 | 个人资料、实名认证（后台审核）、团队/邀请关系树 |
| 会员 | 会员等级（普通 / 高级 / VIP）、会员购买与续期、权益展示 |
| 商品 | 商品分类、商品列表与详情、SKU 模型 |
| 订单 | 创建（BUY / SELL / SERVICE）、支付（余额冻结）、取消（退款解冻）、状态机流转 |
| 预约 | 预约排队，撮合时按预约时间优先 |
| 撮合 | A 订单 → 多 B 订单撮合、实时撮合 + 24h 周期扫描、人工撮合、撮合日志与任务记录 |
| 账户 | 可用 / 冻结 / 待结算余额、全量资金流水、管理员入金/出金调整 |
| 费用 | 平台服务费规则（默认 5%）、费率可配置、历史快照、费用记录 |
| 提现 | 申请 → 审核 → 完成，余额冻结与出账、风控拦截 |
| 团队 | 邀请码生成/禁用、团队统计、推广奖励（绑定真实成交） |
| 客服 | 工单创建、双向消息、关闭 |
| 申诉 | 用户提交申诉，后台处理 |
| 风控 | 风险规则/事件/用户，冻结/禁用动作 |
| 通知 | 站内通知、公告 |
| 管理后台 | Dashboard 统计与图表、用户/订单/撮合/财务/风控/客服/申诉/公告/邀请码管理 |
| RBAC | 管理员、角色、权限点、超级管理员，全部后台接口校验管理员 JWT |
| 审计 | 操作日志（操作者、IP、requestId、前后数据） |
| 运维 | Alembic 迁移、Docker Compose 一键部署、健康检查 |

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2（async）+ Pydantic v2 |
| 数据库 | MySQL 8（utf8mb4，生产）/ SQLite + aiosqlite（本地开发与测试） |
| 缓存/锁/限流 | Redis 7（无 Redis 时降级为进程内 MemoryRedis） |
| 任务 | Celery + Celery Beat + RabbitMQ（关闭时降级为进程内 asyncio 调度器） |
| 用户端 | Vue 3 + TypeScript + Vite + Pinia + Vant 4 |
| 管理后台 | Vue 3 + TypeScript + Element Plus + ECharts |
| 部署 | Docker Compose + Nginx 1.27 |

## 目录结构

```text
TX/
├── .env.example                 # 环境变量样例（后端全部配置）
├── docker-compose.yml           # 9 个服务编排：nginx / backend / celery-worker / celery-beat / mysql / redis / rabbitmq / web / admin
├── nginx/
│   └── nginx.conf               # 入口路由：/ → web，/admin/ → admin，/api/ → backend，/health → backend
├── backend/                     # FastAPI 后端
│   ├── Dockerfile               # 启动前执行 alembic upgrade head，再启动 uvicorn
│   ├── requirements.txt         # 依赖清单（含 pytest / ruff / mypy）
│   ├── pyproject.toml           # pytest / ruff / mypy 配置
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py               # 异步迁移环境，URL 随 settings 动态切换 MySQL / SQLite
│   │   └── versions/
│   │       └── 218608bbc4b0_initial_schema.py   # 初始迁移（48 张表）
│   ├── app/
│   │   ├── main.py              # 应用入口、全局异常处理、健康检查
│   │   ├── config.py            # pydantic-settings 配置（.env）
│   │   ├── database.py          # 异步引擎 / 会话 / Base
│   │   ├── seed.py              # 启动种子：超级管理员、RBAC、默认费率/推广规则、会员等级、示例商品、系统邀请码
│   │   ├── dependencies.py      # 分页 / 幂等 / 限流依赖
│   │   ├── core/                # security(JWT+Argon2) / permissions / response / exceptions / logging
│   │   ├── models/              # SQLAlchemy 模型（用户/账户/订单/撮合/会员/商品/邀请/费用/提现/客服/申诉/风控/通知/后台/审计）
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── services/            # 业务服务（撮合引擎 / 账务 / 订单 / 认证 / 提现 / 风控 / 推广 等）
│   │   ├── api/v1/              # auth / users / invites / memberships / orders / reservations / accounts / finance / support / admin
│   │   ├── tasks/               # celery_app / matching_tasks / order_tasks / scheduler(进程内兜底)
│   │   └── utils/               # 单号与幂等工具 / Redis 客户端（含 MemoryRedis）
│   └── tests/                   # pytest 测试（unit / integration / matching / api），共 35 个用例
├── web/                         # 用户端（Vue 3 + Vant）
│   ├── Dockerfile
│   ├── nginx.conf               # 静态托管 SPA
│   ├── vite.config.ts           # dev 代理 /api → localhost:8000
│   └── src/
│       ├── api/                 # axios 封装与各模块 API
│       ├── stores/              # Pinia（auth）
│       ├── router/              # 前端路由
│       └── views/               # 首页/登录/注册/商品/订单/账户/提现/团队/客服/申诉/通知 等
├── admin/                       # 管理后台（Vue 3 + Element Plus + ECharts）
│   ├── Dockerfile
│   ├── nginx.conf               # 静态托管 SPA（/admin/ 前缀已由入口 nginx 剥离）
│   ├── vite.config.ts           # base=/admin/，dev 端口 5173
│   └── src/
│       ├── api/                 # admin.ts / http.ts / types.ts
│       ├── stores/              # Pinia（auth）
│       ├── router/              # 后台路由
│       ├── layout/              # AdminLayout
│       └── views/               # Dashboard/用户/订单/撮合/财务/风控/客服/申诉/RBAC/日志 等
└── docs                         # 本文档目录（本项目生成的 8 份文档）
    ├── README.md                # 你正在阅读的文件
    ├── ARCHITECTURE.md          # 系统架构与核心流程
    ├── DATABASE.md              # 数据库设计（48 张表）与 Alembic 使用
    ├── API.md                   # 完整 API 清单
    ├── SECURITY.md              # 安全设计
    ├── DEPLOYMENT.md            # 部署与运维
    ├── TESTING.md               # 测试
    └── CHANGELOG.md             # 版本变更记录
```

> 说明：`docs/` 目录是本文档集的物理位置，实际文件位于仓库根目录（即 README.md、ARCHITECTURE.md 等与 docker-compose.yml 同级）。

## 快速开始

### 方式一：Docker 一键部署（推荐）

前置要求：Docker 24+、Docker Compose v2。

```bash
# 1. 准备环境变量（务必修改默认密钥）
cp .env.example .env
#   打开 .env，至少修改：
#   - MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD
#   - REDIS_PASSWORD
#   - RABBITMQ_PASSWORD
#   - JWT_SECRET（用 `openssl rand -hex 32` 生成）

# 2. 构建并启动全部 9 个服务
docker compose up -d --build

# 3. 查看状态（全部 healthy 即就绪）
docker compose ps
```

启动完成后（后台容器会自动执行 `alembic upgrade head` 并初始化种子数据）：

| 入口 | 地址 |
| --- | --- |
| 用户端 | http://localhost/ |
| 管理后台 | http://localhost/admin/ |
| API 基础地址 | http://localhost/api/v1/... |
| 健康检查 | http://localhost/health |

### 方式二：本地开发（无 Docker）

后端在未配置 `MYSQL_HOST` / `REDIS_HOST` / `CELERY_ENABLED=false` 时会自动降级为 SQLite + 进程内 Redis + 进程内调度器，无需任何外部依赖即可跑通。

```bash
# 后端（终端 1）
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows；macOS/Linux 用 source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head             # 建表（或直接启动，init_db 也会建表）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 访问 http://localhost:8000/api/docs（Swagger，FastAPI 默认 /docs）

# 用户端（终端 2）
cd web
npm install
npm run dev                      # dev 已代理 /api → localhost:8000，访问 http://localhost:5173

# 管理后台（终端 3）
cd admin
npm install
npm run dev                      # base=/admin/，dev 端口 5173，访问 http://localhost:5173/admin/
```

## 默认账号

| 账号 | 类型 | 说明 |
| --- | --- | --- |
| `superadmin` / `Admin@123456` | 超级管理员 | 管理后台登录，可在 `.env` 中通过 `ADMIN_INIT_USERNAME` / `ADMIN_INIT_PASSWORD` 覆盖 |

普通用户通过邀请码注册（种子会生成 10 个系统邀请码 `creator_id=0`；系统邀请码不建立上下级关系）。

## 默认配置速查

| 项 | 默认值 | 配置键 |
| --- | --- | --- |
| 服务费率 | 5%（支持 0~100%） | `DEFAULT_SERVICE_FEE_RATE` / `fee_rules` |
| 推广奖励率 | 2%（绑定真实成交） | `promotion_rules`（ORDER_COMMISSION） |
| JWT access 有效期 | 7200 秒（2h） | `JWT_ACCESS_EXPIRE` |
| JWT refresh 有效期 | 2592000 秒（30d） | `JWT_REFRESH_EXPIRE` |
| 撮合扫描间隔 | 开发 60s / 生产 86400s（24h） | `MATCH_SCAN_INTERVAL` / `MATCH_SCAN_INTERVAL_PROD` |
| 提现最低金额 | 100 | `WITHDRAW_MIN_AMOUNT` |
| 提现日限额 | 50000 | `WITHDRAW_DAILY_LIMIT` |

## 文档索引

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 系统架构、模块划分、核心流程、撮合算法与并发安全、事务边界、合规设计
- [DATABASE.md](./DATABASE.md) — 数据库选型、48 张表清单与核心表字段、Alembic 使用方式
- [API.md](./API.md) — 完整 API 清单（鉴权约定、响应包络、分页、全部端点）
- [SECURITY.md](./SECURITY.md) — 安全设计（JWT/Argon2/RBAC/并发锁/幂等/限流/敏感信息不出网等）
- [DEPLOYMENT.md](./DEPLOYMENT.md) — 部署前置、Docker 编排、nginx 路由、本地降级模式、备份与升级
- [TESTING.md](./TESTING.md) — 测试栈、运行方式、覆盖点与当前结果
- [CHANGELOG.md](./CHANGELOG.md) — 版本 1.0.0 变更记录与工程加固明细
