# 部署与运维

本文档说明 LX Platform 的 Docker 部署、Nginx 路由、环境变量、本地开发降级模式、备份与升级。

## 1. 部署前置

- Docker Engine 24+、Docker Compose v2（`docker compose` 子命令）。
- 空闲端口：`80`（唯一对外端口；内网服务均不映射宿主机端口）。
- 磁盘：镜像 + 数据卷预留 ≥ 10GB；建议宿主机时间同步（NTP），保障 JWT `exp` 校验与撮合扫描准确性。

## 2. 服务编排（docker-compose.yml，9 个服务）

| 服务 | 镜像/基座 | 端口 | 说明 |
| --- | --- | --- | --- |
| nginx | nginx:1.27 | **80→80** | 唯一入口，路由见 §4 |
| backend | python:3.12-slim | 内网 8000 | FastAPI；启动命令：`alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| celery-worker | 同上构建 | 内网 | 执行撮合/完成扫描任务 |
| celery-beat | 同上构建 | 内网 | 定时调度（生产 `MATCH_SCAN_INTERVAL_PROD=86400`） |
| mysql | mysql:8.4 | **不发布** | utf8mb4；`--default-authentication-plugin=caching_sha2_password`；数据卷 `mysql_data` |
| redis | redis:7 | **不发布** | 带密码；AOF 持久化 `redis_data` |
| rabbitmq | rabbitmq:3-management | **不发布** | 默认用户/密码为环境变量 |
| web | node:20 构建 → nginx:1.27 | 内网 80 | 用户端 SPA（多阶段构建） |
| admin | node:20 构建 → nginx:1.27 | 内网 80 | 管理后台 SPA（多阶段构建） |

健康检查：backend `/health`；celery-worker/beat `celery -A app.tasks.celery_app inspect ping`；mysql `mysqladmin ping`；redis `redis-cli ping`；rabbitmq `rabbitmq-diagnostics -q ping`；nginx/web/admin `wget /health` 或 `wget -qO- http://localhost`。

## 3. 部署步骤

```bash
# 1) 进入项目根目录
cd TX

# 2) 准备环境变量
cp .env.example .env
#   必须修改（安全要求）：
#   MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD
#   REDIS_PASSWORD
#   RABBITMQ_PASSWORD
#   JWT_SECRET        （openssl rand -hex 32）
#   可选：ADMIN_INIT_USERNAME / ADMIN_INIT_PASSWORD（覆盖默认后台账号）

# 3) 构建并后台启动
docker compose up -d --build

# 4) 等待全部 healthy
docker compose ps
#   首次启动 MySQL 初始化 + alembic upgrade head + 种子数据 约需 1~2 分钟

# 5) 验证
curl http://localhost/health          # 用户端可访问
curl -I http://localhost/admin/       # 后台可访问
curl -s http://localhost/api/v1/fees  # API 正常（公开接口示例）
```

启动完成后后台自动完成：

1. `alembic upgrade head`（建齐 48 张表，幂等）；
2. 种子数据（幂等，重复启动不会重复插入）：超级管理员、RBAC 角色与权限、默认服务费率（5%）、推广规则（2%）、三级会员等级、示例商品与分类、10 个系统邀请码。

## 4. Nginx 路由表（入口 nginx/nginx.conf）

| 路径 | 上游 | 说明 |
| --- | --- | --- |
| `/api/` | `lx_backend:8000` | 后端 API（`proxy_pass http://lx_backend;`，保留 `/api` 前缀） |
| `/admin/` | `lx_admin` | 管理后台 SPA（`proxy_pass http://lx_admin;`，剥离 `/admin/` 前缀） |
| `=/admin` | `lx_admin` | 精确匹配 301 → `/admin/` |
| `=/health` | `lx_backend` | 健康检查（供 LB/编排探活） |
| `/` | `lx_web` | 用户端 SPA |

内置安全头：`X-Content-Type-Options: nosniff`、`X-Frame-Options: SAMEORIGIN`、`X-XSS-Protection: 1; mode=block`、`Referrer-Policy: strict-origin-when-cross-origin`；`client_max_body_size 20m`；日志格式含 `$request_id`。

## 5. 常用运维命令

```bash
# 查看状态与日志
docker compose ps
docker compose logs -f backend
docker compose logs -f celery-worker

# 重启单个服务（修改配置/代码后）
docker compose up -d --build backend

# 重建并全量重启（升级发布）
docker compose up -d --build --remove-orphans

# 停止/启动
docker compose stop
docker compose start
docker compose down          # 保留数据卷
docker compose down -v       # 慎用！会删除 mysql_data / redis_data 数据

# 数据库命令行（容器内）
docker compose exec mysql mysql -uroot -p lx_platform
```

## 6. 本地开发（无 Docker 降级模式）

后端支持在未配置外部中间件时自动降级，零依赖跑通全部业务逻辑：

| 环境变量 | 未设置时 | 效果 |
| --- | --- | --- |
| `MYSQL_HOST`（默认空） | → SQLite（`backend/lx_platform.db`，aiosqlite） | 无需 MySQL |
| `REDIS_HOST`（默认空） | → 进程内 `MemoryRedis` | 锁/限流/验证码仍可用 |
| `CELERY_ENABLED`（默认 false） | → 进程内 asyncio 调度器（`app/tasks/scheduler.py`） | 每 `MATCH_SCAN_INTERVAL`（默认 60s）扫描撮合 |

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                      # Windows；macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head                        # 显式建表（或直接启动，首次启动 init_db 也会建表）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端本地联调：

```bash
# 用户端（dev 已代理 /api → http://localhost:8000）
cd web && npm install && npm run dev        # http://localhost:5173

# 管理后台（base=/admin/，dev 端口 5173，代理同左）
cd admin && npm install && npm run dev      # http://localhost:5173/admin/
```

本地开发 Swagger：`http://localhost:8000/docs`（后端直连）。注意 Nginx 默认仅代理 `/api/`、`/admin/`、`/health`，**默认不暴露 `/docs`**；如需对外提供，在入口 nginx 增加：

```nginx
location /docs {
    proxy_pass http://lx_backend:8000;
}
```

## 7. 环境变量一览（`.env.example`）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` 关闭调试细节 |
| `DEBUG` | `true` | 生产置 `false` |
| `SECRET_KEY` | 随机生成 | 内部使用 |
| `JWT_SECRET` | 内置随机串 | **生产必须替换**（`openssl rand -hex 32`） |
| `JWT_ACCESS_EXPIRE` | 7200 | access 有效期（秒） |
| `JWT_REFRESH_EXPIRE` | 2592000 | refresh 有效期（秒） |
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_DB` / `MYSQL_USER` / `MYSQL_PASSWORD` | 空 | 后端连库；为空走 SQLite |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | 空 | 为空走 MemoryRedis |
| `RABBITMQ_URL` | 空 | Celery broker；`CELERY_ENABLED=false` 时不使用 |
| `CELERY_ENABLED` | `false` | 生产 `true` 使用 Celery；否则进程内调度 |
| `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` | `CHANGE_ME` | **必须修改** |
| `REDIS_PASSWORD` | `CHANGE_ME` | **必须修改** |
| `RABBITMQ_USER` / `RABBITMQ_PASSWORD` | `CHANGE_ME` | **必须修改** |
| `ADMIN_INIT_USERNAME` / `ADMIN_INIT_PASSWORD` | `superadmin` / `Admin@123456` | 种子后台账号 |
| `DEFAULT_SERVICE_FEE_RATE` | `0.05` | 默认服务费率（种子写 fee_rules） |
| `ORDER_COMMISSION_RATE` | `0.02` | 推广奖励率（种子写 promotion_rules） |
| `MATCH_SCAN_INTERVAL` / `MATCH_SCAN_INTERVAL_PROD` | 60 / 86400 | 撮合扫描间隔（秒） |
| `WITHDRAW_MIN_AMOUNT` / `WITHDRAW_DAILY_LIMIT` | 100 / 50000 | 提现限制 |

## 8. 备份与恢复

```bash
# 数据库全量备份（每日执行）
docker compose exec mysql mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" \
  --single-transaction --routines --triggers lx_platform > lx_platform_$(date +%F).sql

# 恢复
docker compose exec -T mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" lx_platform < lx_platform_2026-08-18.sql

# Redis 数据卷（如启用 AOF）
docker run --rm -v tx_redis_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/redis_data.tar.gz -C /data .
```

建议：数据库每日全备 + binlog 增量；`mysql_data`/`redis_data` 卷定期快照；每季度做一次恢复演练。

## 9. 版本升级

1. 拉取新代码：`git pull`（或替换镜像 tag）。
2. 查看新迁移：`alembic history`（本地预览）。
3. 备份数据库（见 §8）。
4. `docker compose up -d --build`——backend 启动时会自动执行 `alembic upgrade head`。
5. 观察 `docker compose logs -f backend` 确认迁移成功、服务 healthy。
6. 升级失败时：检查迁移是否与新增约束冲突；可 `alembic downgrade -1` 回退（生产环境请先在测试环境演练）。

## 10. 常见问题（FAQ）

| 问题 | 处理 |
| --- | --- |
| 80 端口被占用 | 关闭占用程序，或修改 compose 中 nginx 的 `ports: "8080:80"` 后访问 `http://localhost:8080` |
| 后台登录报权限错误 | 确认 `POST /admin/login` 使用 `superadmin` + `.env` 中配置的初始密码；首次登录后立即修改 |
| 前端 404 / 白屏 | 检查入口 nginx `location /admin/` 是否使用 `proxy_pass http://lx_admin;`（不带路径，剥离前缀），web/admin 自身 nginx.conf 的 `try_files` 是否兜底到 `index.html` |
| API 报 502 | backend 未就绪：`docker compose logs -f backend` 查看 alembic 是否卡在迁移 |
| 订单不撮合 | 确认 celery-worker/beat healthy 或降级调度器已启动；观察 `matching_jobs` 记录 |
| 修改代码不生效 | `docker compose up -d --build <服务>`（重新构建镜像） |

## 11. 可观测性建议

- 接入 Prometheus + Grafana：backend 为 FastAPI 可挂载 `/metrics`；celery 有 `celery[flower]` 可选。
- 日志：nginx/backend 均输出结构化日志（含 request_id），可接入 Loki/ELK。
- 告警：磁盘、MySQL 连接数、撮合积压数（`WAITING_MATCH` 订单量）、celery 任务失败率。
