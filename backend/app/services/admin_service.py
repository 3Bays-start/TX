"""管理后台服务：Dashboard / 用户管理 / RBAC / 实名审核 / 日志。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.permissions import PERMISSIONS
from app.core.security import hash_password, verify_password
from app.models.admin import (
    AdminPermission,
    AdminRole,
    AdminRolePermission,
    AdminUser,
    AdminUserRole,
)
from app.models.appeal import Appeal
from app.models.audit import OperationLog
from app.models.fee import FeeRecord
from app.models.order import Order
from app.models.user import User
from app.models.withdrawal import WithdrawalOrder
from app.services.audit_service import write_operation_log

# ===== Dashboard =====

async def dashboard_stats(db: AsyncSession) -> dict:
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    user_total = await db.scalar(select(func.count(User.id))) or 0
    user_today = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= today_start)
    ) or 0
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.last_login_at >= (datetime.now() - timedelta(days=7)))
    ) or 0

    order_total = await db.scalar(select(func.count(Order.id))) or 0
    order_today = await db.scalar(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    ) or 0
    waiting_match = await db.scalar(
        select(func.count(Order.id)).where(Order.status.in_(["WAITING_MATCH", "PARTIAL_MATCHED"]))
    ) or 0
    abnormal_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.status.in_(["DISPUTED", "RISK_REVIEW", "EXPIRED"]))
    ) or 0
    appeal_pending = await db.scalar(
        select(func.count(Appeal.id)).where(Appeal.status == "PENDING")
    ) or 0
    withdrawal_pending = await db.scalar(
        select(func.count(WithdrawalOrder.id)).where(WithdrawalOrder.status.in_(["PENDING", "REVIEWING"]))
    ) or 0
    service_fee_total = await db.scalar(
        select(func.coalesce(func.sum(FeeRecord.fee_amount), 0))
    ) or 0

    # 图表：近 7 天用户增长与订单趋势
    user_growth = []
    order_trend = []
    for i in range(6, -1, -1):
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        user_growth.append(
            await db.scalar(select(func.count(User.id)).where(User.created_at >= day_start, User.created_at < day_end)) or 0
        )
        order_trend.append(
            await db.scalar(select(func.count(Order.id)).where(Order.created_at >= day_start, Order.created_at < day_end)) or 0
        )

    return {
        "user_total": user_total,
        "user_today": user_today,
        "active_users": active_users,
        "order_total": order_total,
        "order_today": order_today,
        "waiting_match": waiting_match,
        "matching": waiting_match,
        "abnormal_orders": abnormal_orders,
        "appeal_pending": appeal_pending,
        "withdrawal_pending": withdrawal_pending,
        "service_fee_total": str(service_fee_total),
        "charts": {"user_growth": user_growth, "order_trend": order_trend},
    }


# ===== 用户管理 =====

async def list_users(db: AsyncSession, filters: dict, page: int, page_size: int) -> tuple[list[User], int]:
    base = select(User)
    if filters.get("phone"):
        base = base.where(User.phone.like(f"%{filters['phone']}%"))
    if filters.get("status"):
        base = base.where(User.status == filters["status"])
    if filters.get("risk_level"):
        base = base.where(User.risk_level == filters["risk_level"])
    if filters.get("user_id"):
        base = base.where(User.id == filters["user_id"])
    if filters.get("keyword"):
        kw = filters["keyword"]
        try:
            kw_id = int(kw)
        except ValueError:
            kw_id = None
        cond = or_(User.username.like(f"%{kw}%"), User.phone.like(f"%{kw}%"))
        if kw_id is not None:
            cond = or_(cond, User.id == kw_id)
        base = base.where(cond)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def set_user_status(db: AsyncSession, admin: AdminUser, user_id: int, status: str, reason: str = "", ip: str = "") -> User:
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("USER_NOT_FOUND", "用户不存在")
    before = user.status
    user.status = status
    await write_operation_log(
        db,
        action="FREEZE" if status == "FROZEN" else ("DISABLE" if status == "DISABLED" else "UNFREEZE"),
        module="user",
        operator_id=admin.id,
        target_type="user",
        target_id=user.id,
        before_data=before,
        after_data=status,
        reason=reason,
        ip=ip,
    )
    return user


# ===== RBAC =====

async def seed_permissions(db: AsyncSession) -> None:
    for code, name in PERMISSIONS.items():
        exists = await db.scalar(select(AdminPermission).where(AdminPermission.code == code))
        if not exists:
            group = code.split(":")[0]
            db.add(AdminPermission(code=code, name=name, group=group))
    await db.flush()


async def seed_system_roles(db: AsyncSession) -> None:
    from app.core.permissions import Perm

    roles = {
        "ADMIN_ORDER": ("订单管理员", [Perm.order_view, Perm.order_operate, Perm.order_match, Perm.user_view]),
        "ADMIN_FINANCE": ("财务管理员", [Perm.account_view, Perm.transaction_view, Perm.withdrawal_view, Perm.withdrawal_review, Perm.fee_view, Perm.fee_edit]),
        "ADMIN_CUSTOMER_SERVICE": ("客服", [Perm.user_view, Perm.order_view, Perm.ticket_view, Perm.ticket_reply, Perm.ticket_assign, Perm.ticket_close, Perm.appeal_view, Perm.appeal_process]),
        "ADMIN_RISK": ("风控专员", [Perm.risk_view, Perm.risk_review, Perm.risk_freeze, Perm.risk_release, Perm.user_freeze]),
    }
    for code, (name, perms) in roles.items():
        role = await db.scalar(select(AdminRole).where(AdminRole.code == code))
        if role:
            continue
        role = AdminRole(code=code, name=name, is_system=True)
        db.add(role)
        await db.flush()
        for pcode in perms:
            perm = await db.scalar(select(AdminPermission).where(AdminPermission.code == pcode))
            if perm:
                db.add(AdminRolePermission(role_id=role.id, permission_id=perm.id))
    await db.flush()


async def create_admin(db: AsyncSession, creator: AdminUser, data: dict, ip: str = "") -> AdminUser:
    exists = await db.scalar(select(AdminUser).where(AdminUser.username == data["username"]))
    if exists:
        raise AppError("ADMIN_EXISTS", "用户名已存在")
    admin = AdminUser(
        username=data["username"],
        password_hash=hash_password(data["password"]),
        nickname=data.get("nickname", ""),
        role_code=data.get("role_code", "ADMIN"),
    )
    db.add(admin)
    await db.flush()
    for rid in data.get("role_ids", []):
        db.add(AdminUserRole(admin_id=admin.id, role_id=rid))
    await write_operation_log(db, "CREATE_ADMIN", module="admin", operator_id=creator.id, target_type="admin", target_id=admin.id, after_data=data, ip=ip)
    return admin


async def update_admin(db: AsyncSession, operator: AdminUser, admin_id: int, data: dict, ip: str = "") -> AdminUser:
    admin = await db.get(AdminUser, admin_id)
    if not admin:
        raise NotFoundError("ADMIN_NOT_FOUND", "管理员不存在")
    if data.get("nickname") is not None:
        admin.nickname = data["nickname"]
    if data.get("password"):
        admin.password_hash = hash_password(data["password"])
    if data.get("status"):
        admin.status = data["status"]
    if data.get("role_ids") is not None:
        existing = (await db.execute(select(AdminUserRole).where(AdminUserRole.admin_id == admin_id))).scalars().all()
        for r in existing:
            await db.delete(r)
        await db.flush()
        for rid in data["role_ids"]:
            db.add(AdminUserRole(admin_id=admin_id, role_id=rid))
    await write_operation_log(db, "UPDATE_ADMIN", module="admin", operator_id=operator.id, target_type="admin", target_id=admin_id, after_data=data, ip=ip)
    return admin


async def create_role(db: AsyncSession, data: dict, ip: str = "") -> AdminRole:
    exists = await db.scalar(select(AdminRole).where(AdminRole.code == data["code"]))
    if exists:
        raise AppError("ROLE_EXISTS", "角色编码已存在")
    role = AdminRole(code=data["code"], name=data["name"], description=data.get("description", ""))
    db.add(role)
    await db.flush()
    for code in data.get("permission_codes", []):
        perm = await db.scalar(select(AdminPermission).where(AdminPermission.code == code))
        if perm:
            db.add(AdminRolePermission(role_id=role.id, permission_id=perm.id))
    await db.flush()
    return role


async def update_role(db: AsyncSession, role_id: int, data: dict) -> AdminRole:
    role = await db.get(AdminRole, role_id)
    if not role:
        raise NotFoundError("ROLE_NOT_FOUND", "角色不存在")
    if data.get("name"):
        role.name = data["name"]
    if data.get("description") is not None:
        role.description = data["description"]
    if data.get("permission_codes") is not None:
        existing = (await db.execute(select(AdminRolePermission).where(AdminRolePermission.role_id == role_id))).scalars().all()
        for r in existing:
            await db.delete(r)
        await db.flush()
        for code in data["permission_codes"]:
            perm = await db.scalar(select(AdminPermission).where(AdminPermission.code == code))
            if perm:
                db.add(AdminRolePermission(role_id=role.id, permission_id=perm.id))
    await db.flush()
    return role


async def role_permissions(db: AsyncSession, role_id: int) -> list[str]:
    stmt = (
        select(AdminPermission.code)
        .join(AdminRolePermission, AdminRolePermission.permission_id == AdminPermission.id)
        .where(AdminRolePermission.role_id == role_id)
    )
    return list((await db.execute(stmt)).scalars().all())


async def admin_permissions(db: AsyncSession, admin_id: int) -> list[str]:
    admin = await db.get(AdminUser, admin_id)
    if not admin:
        return []
    if admin.is_super or admin.role_code == "SUPER_ADMIN":
        stmt = select(AdminPermission.code)
        return list((await db.execute(stmt)).scalars().all())
    stmt = (
        select(AdminPermission.code)
        .join(AdminRolePermission, AdminRolePermission.permission_id == AdminPermission.id)
        .join(AdminUserRole, AdminUserRole.role_id == AdminRolePermission.role_id)
        .where(AdminUserRole.admin_id == admin_id)
    )
    return list((await db.execute(stmt)).scalars().all())


# ===== 日志 =====

async def list_operation_logs(db: AsyncSession, page: int, page_size: int) -> tuple[list[OperationLog], int]:
    base = select(OperationLog).order_by(OperationLog.id.desc())
    total = len((await db.execute(base)).scalars().all())
    stmt = base.offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


# ===== 管理员登录 =====

async def admin_login(db: AsyncSession, username: str, password: str) -> tuple[AdminUser, list[str]]:
    admin = await db.scalar(select(AdminUser).where(AdminUser.username == username))
    if not admin or not verify_password(password, admin.password_hash):
        raise AppError("AUTH_INVALID", "用户名或密码错误")
    if admin.status != "ACTIVE":
        raise AppError("AUTH_INVALID", "管理员已禁用")
    admin.last_login_at = datetime.now()
    perms = await admin_permissions(db, admin.id)
    return admin, perms


async def get_admin_detail(db: AsyncSession, admin_id: int) -> tuple[AdminUser, list[str]]:
    admin = await db.get(AdminUser, admin_id)
    if not admin:
        raise NotFoundError("ADMIN_NOT_FOUND", "管理员不存在")
    perms = await admin_permissions(db, admin_id)
    return admin, perms
