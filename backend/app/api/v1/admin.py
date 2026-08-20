"""管理后台路由：Dashboard / 用户 / 订单 / 撮合 / 财务 / 风控 / 客服 / RBAC / 日志。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    AppError,
    NotFoundError,
    PermissionDeniedError,
    UserDisabledError,
    UserFrozenError,
)
from app.core.permissions import _load_admin_permissions
from app.core.response import success
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import RateLimiter, get_page_params
from app.models.account import Account, AccountTransaction
from app.models.admin import AdminPermission, AdminRole, AdminUser
from app.models.appeal import Appeal
from app.models.fee import FeeRecord, FeeRule
from app.models.matching import MatchingJob, MatchLog, MatchOrder
from app.models.order import Order, OrderStatusLog
from app.models.promotion import PromotionRecord
from app.models.risk import RiskEvent
from app.models.support import SupportTicket
from app.models.user import User
from app.models.withdrawal import WithdrawalOrder
from app.schemas.admin import (
    AdminLoginRequest,
    AdminUserCreate,
    AdminUserUpdate,
    RoleCreate,
    WithdrawalReviewRequest,
)
from app.schemas.auth import ChangePasswordRequest
from app.schemas.common import PageParams
from app.services import (
    account_service,
    admin_service,
    appeal_service,
    matching_service,
    support_service,
    withdrawal_service,
)
from app.services.audit_service import write_operation_log
from app.services.auth_service import get_current_admin as _get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


async def _user_info_map(db: AsyncSession, user_ids: set[int]) -> dict[int, dict[str, str]]:
    """批量查询用户昵称/账号，供列表接口展示「昵称（账号）」而非用户ID。"""
    if not user_ids:
        return {}
    users = {
        u.id: u
        for u in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    }
    return {
        uid: {
            "user_nickname": u.nickname,
            "user_username": u.username or "",
            "user_phone": u.phone or "",
        }
        for uid, u in users.items()
    }


def _client(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd and settings.TRUSTED_PROXY:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def _credit_name(levels: list, completed_orders: int) -> str:
    current = levels[0] if levels else None
    for level in levels:
        if level.min_orders <= completed_orders:
            current = level
    return current.name if current else "普通"


def admin_service_me(permission: str | None = None):
    """当前管理员依赖；指定 permission 时校验 RBAC（超管放行）。"""

    async def _checker(
        request: Request,
        authorization: str | None = Header(default=None),
        db: AsyncSession = Depends(get_db),
    ) -> AdminUser:
        admin = await _get_current_admin(request, authorization, db)
        if permission and admin.role_code != "SUPER_ADMIN" and not admin.is_super:
            perms = await _load_admin_permissions(db, admin.id)
            if permission not in perms:
                raise PermissionDeniedError()
        return admin

    return _checker


# ===== 认证 =====

@router.post("/login", dependencies=[Depends(RateLimiter(5, 60))])
async def admin_login(payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    from app.services.admin_service import admin_login as _login

    admin, perms = await _login(db, payload.username, payload.password)
    token = create_access_token(admin.id, role="admin")
    return success(
        {
            "access_token": token,
            "expires_in": settings.JWT_ACCESS_EXPIRE,
            "admin": {"id": admin.id, "username": admin.username, "nickname": admin.nickname, "is_super": admin.is_super},
            "permissions": perms,
        },
        "登录成功",
    )


@router.get("/me")
async def admin_me(admin: AdminUser = Depends(admin_service_me()), db: AsyncSession = Depends(get_db)):
    _, perms = await admin_service.get_admin_detail(db, admin.id)
    return success({"id": admin.id, "username": admin.username, "nickname": admin.nickname, "role_code": admin.role_code, "is_super": admin.is_super, "permissions": perms})


@router.post("/me/password", dependencies=[Depends(RateLimiter(10, 60))])
async def admin_change_password(
    payload: ChangePasswordRequest,
    admin: AdminUser = Depends(admin_service_me()),
    db: AsyncSession = Depends(get_db),
):
    """当前登录管理员修改自己的密码。"""
    if not verify_password(payload.old_password, admin.password_hash):
        raise AppError("PASSWORD_INCORRECT", "原密码错误")
    admin.password_hash = hash_password(payload.new_password)
    await db.flush()
    await write_operation_log(
        db, "CHANGE_PASSWORD", module="auth", operator_id=admin.id,
        target_type="admin", target_id=admin.id, ip="",
    )
    return success(None, "密码已修改")


# ===== Dashboard =====

@router.get("/dashboard")
async def dashboard(admin: AdminUser = Depends(admin_service_me()), db: AsyncSession = Depends(get_db)):
    return success(await admin_service.dashboard_stats(db))


# ===== 用户管理 =====

@router.get("/users")
async def list_users(
    user_id: int | None = None,
    phone: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    risk_level: str | None = None,
    admin: AdminUser = Depends(admin_service_me('user:view')),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    items, total = await admin_service.list_users(
        db,
        {"user_id": user_id, "phone": phone, "keyword": keyword, "status": status, "risk_level": risk_level},
        params.page,
        params.page_size,
    )
    from app.services.credit_service import list_credit_levels

    levels = await list_credit_levels(db)
    return success(
        {
            "items": [
                {
                    "id": u.id,
                    "username": u.username or "",
                    "phone": u.phone or "",
                    "nickname": u.nickname,
                    "status": u.status,
                    "risk_level": u.risk_level,
                    "completed_order_count": u.completed_order_count or 0,
                    "credit_level_name": _credit_name(levels, u.completed_order_count or 0),
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                }
                for u in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )


@router.get("/users/{user_id}")
async def user_detail(user_id: int, admin: AdminUser = Depends(admin_service_me('user:view')), db: AsyncSession = Depends(get_db)):
    from app.services.user_service import get_credit_level

    user = await db.get(User, user_id)
    if not user:
        return success(None, "用户不存在")
    account = await db.scalar(select(Account).where(Account.user_id == user_id))
    credit_name, credit_code = await get_credit_level(db, user.completed_order_count or 0)
    return success(
        {
            "id": user.id,
            "username": user.username or "",
            "phone": user.phone or "",
            "nickname": user.nickname,
            "avatar": user.avatar,
            "status": user.status,
            "risk_level": user.risk_level,
            "register_ip": user.register_ip,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "credit_level": user.completed_order_count or 0,
            "credit_level_name": credit_name,
            "credit_level_code": credit_code,
            "account": {
                "available_amount": str(account.available_amount) if account else "0",
                "frozen_amount": str(account.frozen_amount) if account else "0",
            },
        }
    )


@router.post("/users/{user_id}/freeze")
async def freeze_user(
    user_id: int,
    request: Request,
    payload: dict | None = None,
    admin: AdminUser = Depends(admin_service_me('user:freeze')),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.set_user_status(db, admin, user_id, "FROZEN", (payload or {}).get("reason", ""), _client(request))
    return success(None, "用户已冻结")


@router.post("/users/{user_id}/unfreeze")
async def unfreeze_user(
    user_id: int,
    request: Request,
    payload: dict | None = None,
    admin: AdminUser = Depends(admin_service_me('user:freeze')),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.set_user_status(db, admin, user_id, "ACTIVE", (payload or {}).get("reason", ""), _client(request))
    return success(None, "用户已解冻")


@router.post("/users/{user_id}/adjust")
async def adjust_balance(
    user_id: int,
    payload: dict,
    request: Request,
    admin: AdminUser = Depends(admin_service_me('user:adjust')),
    db: AsyncSession = Depends(get_db),
):
    from decimal import Decimal

    await account_service.admin_adjust(db, admin.id, user_id, Decimal(str(payload["amount"])), payload.get("reason", ""))
    await write_operation_log(
        db, "ADJUST_BALANCE", "finance", "ADMIN", admin.id, "user", user_id,
        after_data=payload, reason=payload.get("reason", ""), ip=_client(request),
    )
    return success(None, "余额调整完成")


@router.post("/users/{user_id}/switch-login")
async def switch_login(
    user_id: int,
    request: Request,
    admin: AdminUser = Depends(admin_service_me('user:view')),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, user_id)
    if not target:
        raise NotFoundError("USER_NOT_FOUND", "用户不存在")
    if target.status == "DISABLED":
        raise UserDisabledError()
    if target.status == "FROZEN":
        raise UserFrozenError()
    from app.core.security import create_refresh_token

    tokens = {
        "access_token": create_access_token(target.id, role="user"),
        "refresh_token": create_refresh_token(target.id, role="user"),
        "expires_in": settings.JWT_ACCESS_EXPIRE,
    }
    await write_operation_log(
        db,
        action="SWITCH_LOGIN",
        module="user",
        operator_id=admin.id,
        target_type="user",
        target_id=target.id,
        ip=_client(request),
    )
    return success(tokens, "登录成功")


# ===== 订单管理 =====

@router.get("/orders")
async def list_orders(
    order_no: str | None = None,
    status: str | None = None,
    order_type: str | None = None,
    user_id: int | None = None,
    admin: AdminUser = Depends(admin_service_me('order:view')),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(Order)
    if order_no:
        base = base.where(Order.order_no.like(f"%{order_no}%"))
    if status:
        base = base.where(Order.status == status)
    if order_type:
        base = base.where(Order.order_type == order_type)
    if user_id:
        base = base.where(Order.user_id == user_id)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(Order.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    users = await _user_info_map(db, {o.user_id for o in items})
    return success(
        {
            "items": [
                {
                    "id": o.id,
                    "order_no": o.order_no,
                    "user_id": o.user_id,
                    **users.get(o.user_id, {}),
                    "order_type": o.order_type,
                    "product_name": o.product_name,
                    "total_amount": str(o.total_amount),
                    "service_fee": str(o.service_fee),
                    "matched_amount": str(o.matched_amount),
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )


@router.get("/orders/{order_id}")
async def order_detail(order_id: int, admin: AdminUser = Depends(admin_service_me('order:view')), db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order:
        return success(None, "订单不存在")
    logs = list((await db.execute(select(OrderStatusLog).where(OrderStatusLog.order_id == order_id))).scalars().all())
    matches = list((await db.execute(select(MatchOrder).where(MatchOrder.parent_order_id == order_id))).scalars().all())
    users = await _user_info_map(db, {order.user_id} | {m.seller_user_id for m in matches})
    order_user = users.get(order.user_id, {})
    return success(
        {
            "id": order.id,
            "order_no": order.order_no,
            "user_id": order.user_id,
            **order_user,
            "order_type": order.order_type,
            "product_name": order.product_name,
            "total_amount": str(order.total_amount),
            "service_fee": str(order.service_fee),
            "payable_amount": str(order.payable_amount),
            "matched_amount": str(order.matched_amount),
            "status": order.status,
            "reservation_time": order.reservation_time.isoformat() if order.reservation_time else None,
            "remark": order.remark,
            "proof_urls": [u for u in (order.proof_urls or "").split(",") if u],
            "proof_submitted_at": order.proof_submitted_at.isoformat() if order.proof_submitted_at else None,
            "created_at": order.created_at.isoformat() if order.created_at else None,
    "status_logs": [
        {"from_status": log.from_status, "to_status": log.to_status, "reason": log.reason, "created_at": log.created_at.isoformat() if log.created_at else None}
        for log in logs
    ],
            "matches": [
                {
                    "match_no": m.match_no,
                    "buyer_order_id": m.buyer_order_id,
                    "seller_order_id": m.seller_order_id,
                    "seller_user_id": m.seller_user_id,
                    "seller_nickname": users.get(m.seller_user_id, {}).get("user_nickname", ""),
                    "seller_phone": users.get(m.seller_user_id, {}).get("user_phone", ""),
                    "match_amount": str(m.match_amount),
                    "status": m.status,
                }
                for m in matches
            ],
        }
    )


@router.post("/matching/manual")
async def manual_batch_match(
    request: Request,
    payload: dict,
    admin: AdminUser = Depends(admin_service_me('order:match')),
    db: AsyncSession = Depends(get_db),
):
    buy_ids = [int(i) for i in (payload.get("buy_order_ids") or [])]
    sell_ids = [int(i) for i in (payload.get("sell_order_ids") or [])]
    reason = payload.get("reason", "管理员手动撮合")
    if not buy_ids or not sell_ids:
        raise AppError("MATCH_PARAM_INVALID", "请同时勾选买入与卖出订单")
    result = await matching_service.match_selected(db, buy_ids, sell_ids, reason)
    await db.flush()
    db.add(
        MatchLog(
            match_no="",
            parent_order_id=buy_ids[0],
            action="MANUAL_MATCH",
            detail=f"批量手动撮合 buy_ids={buy_ids} sell_ids={sell_ids} 结果={result}",
            operator_type="ADMIN",
            operator_id=admin.id,
        )
    )
    await write_operation_log(
        db, "MANUAL_MATCH", "matching", "ADMIN", admin.id, "order", buy_ids[0],
        after_data={"buy_order_ids": buy_ids, "sell_order_ids": sell_ids, "result": result},
        reason=reason, ip=_client(request),
    )
    return success(result, "撮合任务已执行")


@router.post("/matching/auto")
async def auto_match(
    request: Request,
    admin: AdminUser = Depends(admin_service_me('order:match')),
    db: AsyncSession = Depends(get_db),
):
    result = await matching_service.scan_pending_orders()
    await write_operation_log(
        db, "AUTO_MATCH", "matching", "ADMIN", admin.id, "order", None,
        after_data=result, reason="后台自动撮合", ip=_client(request),
    )
    return success(result, "自动撮合完成")


# ===== 撮合管理 =====

@router.get("/matching")
async def matching_list(
    status: str | None = None,
    admin: AdminUser = Depends(admin_service_me('order:view')),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(Order).where(Order.status.in_(["WAITING_MATCH", "PARTIAL_MATCHED", "FULL_MATCHED"]))
    if status:
        base = base.where(Order.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(Order.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    users = await _user_info_map(db, {o.user_id for o in items})
    return success(
        {
            "items": [
                {
                    "id": o.id,
                    "order_no": o.order_no,
                    "user_id": o.user_id,
                    **users.get(o.user_id, {}),
                    "order_type": o.order_type,
                    "target_amount": str(o.total_amount),
                    "matched_amount": str(o.matched_amount),
                    "remaining_amount": str(o.total_amount - o.matched_amount),
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )


@router.get("/matching/jobs")
async def matching_jobs(admin: AdminUser = Depends(admin_service_me('order:view')), db: AsyncSession = Depends(get_db), params: PageParams = Depends(get_page_params)):
    base = select(MatchingJob)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(MatchingJob.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return success(
        {
            "items": [
                {
                    "job_id": j.job_id,
                    "start_time": j.start_time.isoformat() if j.start_time else None,
                    "end_time": j.end_time.isoformat() if j.end_time else None,
                    "processed_count": j.processed_count,
                    "success_count": j.success_count,
                    "failed_count": j.failed_count,
                    "status": j.status,
                }
                for j in items
            ],
            "total": total,
        }
    )


# ===== 财务 =====

@router.get("/accounts/{user_id}")
async def user_account(user_id: int, admin: AdminUser = Depends(admin_service_me('account:view')), db: AsyncSession = Depends(get_db)):
    account = await account_service.ensure_account(db, user_id)
    return success(
        {
            "account_no": account.account_no,
            "available_amount": str(account.available_amount),
            "frozen_amount": str(account.frozen_amount),
            "pending_amount": str(account.pending_amount),
        }
    )


@router.get("/transactions")
async def transactions(
    user_id: int | None = None,
    business_type: str | None = None,
    admin: AdminUser = Depends(admin_service_me('transaction:view')),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(AccountTransaction)
    if user_id:
        base = base.where(AccountTransaction.user_id == user_id)
    if business_type:
        base = base.where(AccountTransaction.business_type == business_type)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(AccountTransaction.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    users = await _user_info_map(db, {t.user_id for t in items})
    return success(
        {
            "items": [
                {
                    "transaction_no": t.transaction_no,
                    "user_id": t.user_id,
                    **users.get(t.user_id, {}),
                    "business_type": t.business_type,
                    "amount": str(t.amount),
                    "before_balance": str(t.before_balance),
                    "after_balance": str(t.after_balance),
                    "direction": t.direction,
                    "reason": t.reason,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in items
            ],
            "total": total,
        }
    )


@router.get("/withdrawals")
async def withdrawals(
    status: str | None = None,
    admin: AdminUser = Depends(admin_service_me('withdrawal:view')),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(WithdrawalOrder)
    if status:
        base = base.where(WithdrawalOrder.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(WithdrawalOrder.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    users = await _user_info_map(db, {w.user_id for w in items})
    return success(
        {
            "items": [
                {
                    "id": w.id,
                    "withdrawal_no": w.withdrawal_no,
                    "user_id": w.user_id,
                    **users.get(w.user_id, {}),
                    "amount": str(w.amount),
                    "actual_amount": str(w.actual_amount),
                    "usdt_address": w.usdt_address,
                    "status": w.status,
                    "review_reason": w.review_reason,
                    "created_at": w.created_at.isoformat() if w.created_at else None,
                }
                for w in items
            ],
            "total": total,
        }
    )


@router.post("/withdrawals/{withdrawal_id}/review")
async def review_withdrawal(
    withdrawal_id: int,
    payload: WithdrawalReviewRequest,
    admin: AdminUser = Depends(admin_service_me('withdrawal:review')),
    db: AsyncSession = Depends(get_db),
):
    await withdrawal_service.review_withdrawal(db, withdrawal_id, admin.id, payload.approve, payload.reason)
    return success(None, "审核完成")


@router.post("/withdrawals/{withdrawal_id}/complete")
async def complete_withdrawal(
    withdrawal_id: int,
    admin: AdminUser = Depends(admin_service_me('withdrawal:review')),
    db: AsyncSession = Depends(get_db),
):
    await withdrawal_service.complete_withdrawal(db, withdrawal_id, admin.id)
    return success(None, "提现已完成")


@router.get("/fees")
async def fees(admin: AdminUser = Depends(admin_service_me('fee:view')), db: AsyncSession = Depends(get_db)):
    rules = list((await db.execute(select(FeeRule))).scalars().all())
    return success(
        {
            "items": [
                {
                    "id": r.id,
                    "fee_type": r.fee_type,
                    "name": r.name,
                    "rate": str(r.rate),
                    "min_fee": str(r.min_fee),
                    "max_fee": str(r.max_fee),
                    "status": r.status,
                    "effective_at": r.effective_at.isoformat() if r.effective_at else None,
                }
                for r in rules
            ]
        }
    )


@router.put("/fees/{fee_type}")
async def update_fee(
    fee_type: str,
    payload: dict,
    admin: AdminUser = Depends(admin_service_me('fee:edit')),
    db: AsyncSession = Depends(get_db),
):
    from decimal import Decimal

    rule = await db.scalar(select(FeeRule).where(FeeRule.fee_type == fee_type))
    if not rule:
        rule = FeeRule(fee_type=fee_type, name=payload.get("name", "服务费"), status="ACTIVE")
        db.add(rule)
    before = {"rate": str(rule.rate), "min_fee": str(rule.min_fee), "max_fee": str(rule.max_fee), "status": rule.status}
    rule.rate = Decimal(str(payload.get("rate", rule.rate)))
    rule.min_fee = Decimal(str(payload.get("min_fee", rule.min_fee)))
    rule.max_fee = Decimal(str(payload.get("max_fee", rule.max_fee)))
    if payload.get("name"):
        rule.name = payload["name"]
    if payload.get("status"):
        rule.status = payload["status"]
    await write_operation_log(db, "UPDATE_FEE", "finance", "ADMIN", admin.id, "fee_rule", rule.id, before_data=before, after_data={"rate": str(rule.rate)})
    return success(None, "费率已更新")


@router.get("/fees/records")
async def fee_records(admin: AdminUser = Depends(admin_service_me('fee:view')), db: AsyncSession = Depends(get_db), params: PageParams = Depends(get_page_params)):
    base = select(FeeRecord)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(FeeRecord.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return success(
        {
            "items": [
                {
                    "fee_no": r.fee_no,
                    "order_id": r.order_id,
                    "fee_type": r.fee_type,
                    "base_amount": str(r.base_amount),
                    "rate": str(r.rate),
                    "fee_amount": str(r.fee_amount),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in items
            ],
            "total": total,
        }
    )


@router.get("/promotions")
async def promotions(admin: AdminUser = Depends(admin_service_me('account:view')), db: AsyncSession = Depends(get_db), params: PageParams = Depends(get_page_params)):
    base = select(PromotionRecord)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(PromotionRecord.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    users = await _user_info_map(db, {r.source_user_id for r in items} | {r.beneficiary_user_id for r in items})
    return success(
        {
            "items": [
                {
                    "record_no": r.record_no,
                    "source_user_id": r.source_user_id,
                    **{f"source_{k}": v for k, v in users.get(r.source_user_id, {}).items()},
                    "source_order_id": r.source_order_id,
                    "beneficiary_user_id": r.beneficiary_user_id,
                    **{f"beneficiary_{k}": v for k, v in users.get(r.beneficiary_user_id, {}).items()},
                    "reward_amount": str(r.reward_amount),
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in items
            ],
            "total": total,
        }
    )


# ===== 风控 =====

@router.get("/risk/events")
async def risk_events(
    status: str | None = None,
    admin: AdminUser = Depends(admin_service_me('risk:view')),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    items, total = await risk_service_list(db, status, params.page, params.page_size)
    users = await _user_info_map(db, {e.user_id for e in items})
    return success(
        {
            "items": [
                {
                    "id": e.id,
                    "event_no": e.event_no,
                    "user_id": e.user_id,
                    **users.get(e.user_id, {}),
                    "rule_code": e.rule_code,
                    "level": e.level,
                    "action": e.action,
                    "detail": e.detail,
                    "status": e.status,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in items
            ],
            "total": total,
        }
    )


async def risk_service_list(db: AsyncSession, status: str | None, page: int, page_size: int):
    from app.services.risk_service import list_risk_events

    return await list_risk_events(db, page, page_size, status)


@router.post("/risk/events/{event_id}/review")
async def review_risk_event(
    event_id: int,
    payload: dict,
    admin: AdminUser = Depends(admin_service_me('risk:review')),
    db: AsyncSession = Depends(get_db),
):
    from app.services.risk_service import apply_risk_action

    event = await db.get(RiskEvent, event_id)
    if not event:
        return success(None, "风险事件不存在")
    if payload.get("approve"):
        await apply_risk_action(db, event.user_id, payload.get("action", event.action), payload.get("reason", ""))
        event.status = "RESOLVED"
    else:
        event.status = "DISMISSED"
    event.processed_by = admin.id
    from datetime import datetime

    event.processed_at = datetime.now()
    return success(None, "风控事件已处理")


# ===== 客服 =====

@router.get("/tickets")
async def tickets(
    status: str | None = None,
    admin: AdminUser = Depends(admin_service_me('ticket:view')),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(SupportTicket)
    if status:
        base = base.where(SupportTicket.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(SupportTicket.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    users = await _user_info_map(db, {t.user_id for t in items})
    return success(
        {
            "items": [
                {
                    "id": t.id,
                    "ticket_no": t.ticket_no,
                    "user_id": t.user_id,
                    **users.get(t.user_id, {}),
                    "category": t.category,
                    "title": t.title,
                    "priority": t.priority,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in items
            ],
            "total": total,
        }
    )


@router.post("/tickets/{ticket_id}/reply")
async def ticket_reply(
    ticket_id: int,
    payload: dict,
    admin: AdminUser = Depends(admin_service_me('ticket:reply')),
    db: AsyncSession = Depends(get_db),
):
    await support_service.add_message(db, ticket_id, "ADMIN", admin.id, payload.get("content", ""), payload.get("attachments", ""))
    return success(None, "回复成功")


@router.post("/tickets/{ticket_id}/close")
async def ticket_close(ticket_id: int, admin: AdminUser = Depends(admin_service_me('ticket:close')), db: AsyncSession = Depends(get_db)):
    await support_service.close_ticket(db, ticket_id, admin.id)
    return success(None, "工单已关闭")


# ===== 申诉 =====

@router.get("/appeals")
async def appeals(
    status: str | None = None,
    admin: AdminUser = Depends(admin_service_me('appeal:view')),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(Appeal)
    if status:
        base = base.where(Appeal.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(Appeal.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    users = await _user_info_map(db, {a.user_id for a in items})
    return success(
        {
            "items": [
                {
                    "id": a.id,
                    "appeal_no": a.appeal_no,
                    "user_id": a.user_id,
                    **users.get(a.user_id, {}),
                    "order_id": a.order_id,
                    "subject": a.subject,
                    "status": a.status,
                    "result": a.result,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in items
            ],
            "total": total,
        }
    )


@router.post("/appeals/{appeal_id}/process")
async def process_appeal(
    appeal_id: int,
    payload: dict,
    admin: AdminUser = Depends(admin_service_me('appeal:process')),
    db: AsyncSession = Depends(get_db),
):
    await appeal_service.process_appeal(db, appeal_id, admin.id, payload.get("approve", False), payload.get("result", ""))
    return success(None, "申诉已处理")


# ===== RBAC 管理员 =====

@router.get("/admins")
async def admins(admin: AdminUser = Depends(admin_service_me('system:admin')), db: AsyncSession = Depends(get_db)):
    items = list((await db.execute(select(AdminUser))).scalars().all())
    return success(
        {
            "items": [
                {
                    "id": a.id,
                    "username": a.username,
                    "nickname": a.nickname,
                    "role_code": a.role_code,
                    "status": a.status,
                    "is_super": a.is_super,
                    "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
                }
                for a in items
            ]
        }
    )


@router.post("/admins")
async def create_admin(
    payload: AdminUserCreate,
    admin: AdminUser = Depends(admin_service_me('system:admin')),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.create_admin(db, admin, payload.model_dump())
    return success(None, "管理员已创建")


@router.put("/admins/{admin_id}")
async def update_admin(
    admin_id: int,
    payload: AdminUserUpdate,
    admin: AdminUser = Depends(admin_service_me('system:admin')),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.update_admin(db, admin, admin_id, payload.model_dump(exclude_none=True))
    return success(None, "管理员已更新")


@router.get("/roles")
async def roles(admin: AdminUser = Depends(admin_service_me('system:role')), db: AsyncSession = Depends(get_db)):
    items = list((await db.execute(select(AdminRole))).scalars().all())
    result = []
    for r in items:
        perms = await admin_service.role_permissions(db, r.id)
        result.append(
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "description": r.description,
                "is_system": r.is_system,
                "permission_codes": perms,
            }
        )
    return success({"items": result})


@router.post("/roles")
async def create_role(payload: RoleCreate, admin: AdminUser = Depends(admin_service_me('system:role')), db: AsyncSession = Depends(get_db)):
    await admin_service.create_role(db, payload.model_dump())
    return success(None, "角色已创建")


@router.put("/roles/{role_id}")
async def update_role(role_id: int, payload: dict, admin: AdminUser = Depends(admin_service_me('system:role')), db: AsyncSession = Depends(get_db)):
    await admin_service.update_role(db, role_id, payload)
    return success(None, "角色已更新")


@router.get("/permissions")
async def permissions(admin: AdminUser = Depends(admin_service_me('system:role')), db: AsyncSession = Depends(get_db)):
    items = list((await db.execute(select(AdminPermission).order_by(AdminPermission.group))).scalars().all())
    return success(
        {
            "items": [
                {"code": p.code, "name": p.name, "group": p.group, "description": p.description}
                for p in items
            ]
        }
    )


# ===== 日志 =====

@router.get("/logs")
async def logs(admin: AdminUser = Depends(admin_service_me('system:log')), db: AsyncSession = Depends(get_db), params: PageParams = Depends(get_page_params)):
    items, total = await admin_service.list_operation_logs(db, params.page, params.page_size)
    return success(
        {
            "items": [
                {
                    "id": log.id,
                    "operator_type": log.operator_type,
                    "operator_id": log.operator_id,
                    "action": log.action,
                    "module": log.module,
                    "target_type": log.target_type,
                    "target_id": log.target_id,
                    "reason": log.reason,
                    "ip": log.ip,
                    "request_id": log.request_id,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in items
            ],
            "total": total,
        }
    )


@router.post("/invites")
async def create_system_invites(
    payload: dict | None = None,
    admin: AdminUser = Depends(admin_service_me('user:view')),
    db: AsyncSession = Depends(get_db),
):
    from app.services.invite_service import create_invite_codes

    payload = payload or {}
    codes = await create_invite_codes(
        db, None, payload.get("count", 10), payload.get("expires_in_days")
    )
    return success(
        {"items": [{"id": c.id, "code": c.code} for c in codes]},
        "系统邀请码已生成",
    )


# ===== 公告 =====

@router.get("/announcements")
async def admin_announcements(admin: AdminUser = Depends(admin_service_me('system:announcement')), db: AsyncSession = Depends(get_db)):
    from app.models.notification import Announcement

    items = list((await db.execute(select(Announcement).order_by(Announcement.id.desc()))).scalars().all())
    return success(
        {
            "items": [
                {
                    "id": a.id,
                    "title": a.title,
                    "content": a.content,
                    "type": a.type,
                    "status": a.status,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                }
                for a in items
            ]
        }
    )


@router.post("/announcements")
async def create_announcement(
    payload: dict,
    admin: AdminUser = Depends(admin_service_me('system:announcement')),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime

    from app.models.notification import Announcement

    a = Announcement(
        title=payload["title"],
        content=payload.get("content", ""),
        type=payload.get("type", "NOTICE"),
        status="ACTIVE",
        publisher_id=admin.id,
        published_at=datetime.now(),
    )
    db.add(a)
    await db.flush()
    return success({"id": a.id}, "公告已发布")
