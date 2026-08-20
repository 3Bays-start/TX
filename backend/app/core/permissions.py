"""权限常量与 RBAC 依赖。"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError
from app.database import get_db
from app.services.auth_service import get_current_admin

# 权限点定义
PERMISSIONS: dict[str, str] = {
    # 用户
    "user:view": "查看用户",
    "user:freeze": "冻结/解冻用户",
    "user:disable": "禁用用户",
    "user:adjust": "人工调整账户",
    # 订单
    "order:view": "查看订单",
    "order:operate": "操作订单",
    "order:match": "人工撮合",
    # 客服
    "ticket:view": "查看工单",
    "ticket:reply": "回复工单",
    "ticket:assign": "分配工单",
    "ticket:close": "关闭工单",
    "appeal:view": "查看申诉",
    "appeal:process": "处理申诉",
    # 财务
    "account:view": "查看账户",
    "transaction:view": "查看流水",
    "withdrawal:view": "查看提现",
    "withdrawal:review": "审核提现",
    "fee:view": "查看费率",
    "fee:edit": "修改费率",
    # 风控
    "risk:view": "查看风控",
    "risk:review": "风控审核",
    "risk:freeze": "风控冻结",
    "risk:release": "风控解冻",
    # 会员
    "membership:view": "查看会员",
    "membership:edit": "管理会员",
    # 系统
    "system:config": "系统配置",
    "system:admin": "管理员管理",
    "system:role": "角色权限管理",
    "system:log": "日志审计",
    "system:announcement": "公告管理",
}


class Perm:
    user_view = "user:view"
    user_freeze = "user:freeze"
    user_disable = "user:disable"
    user_adjust = "user:adjust"
    order_view = "order:view"
    order_operate = "order:operate"
    order_match = "order:match"
    ticket_view = "ticket:view"
    ticket_reply = "ticket:reply"
    ticket_assign = "ticket:assign"
    ticket_close = "ticket:close"
    appeal_view = "appeal:view"
    appeal_process = "appeal:process"
    account_view = "account:view"
    transaction_view = "transaction:view"
    withdrawal_view = "withdrawal:view"
    withdrawal_review = "withdrawal:review"
    fee_view = "fee:view"
    fee_edit = "fee:edit"
    risk_view = "risk:view"
    risk_review = "risk:review"
    risk_freeze = "risk:freeze"
    risk_release = "risk:release"
    membership_view = "membership:view"
    membership_edit = "membership:edit"
    system_config = "system:config"
    system_admin = "system:admin"
    system_role = "system:role"
    system_log = "system:log"
    system_announcement = "system:announcement"


def require_permission(permission: str) -> Callable:
    async def checker(
        admin=Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if admin.role_code == "SUPER_ADMIN":
            return
        perm_set = await _load_admin_permissions(db, admin.id)
        if permission not in perm_set:
            raise PermissionDeniedError()

    return checker


async def _load_admin_permissions(db: AsyncSession, admin_id: int) -> set[str]:
    from sqlalchemy import select

    from app.models.admin import AdminPermission, AdminRolePermission, AdminUserRole

    stmt = (
        select(AdminPermission.code)
        .join(AdminRolePermission, AdminRolePermission.permission_id == AdminPermission.id)
        .join(AdminUserRole, AdminUserRole.role_id == AdminRolePermission.role_id)
        .where(AdminUserRole.admin_id == admin_id)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)
