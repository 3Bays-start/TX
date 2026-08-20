"""模型公共基类与常量。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

# SQLite 不支持 BigInteger 自增，使用方言变体
PK_TYPE = BigInteger().with_variant(Integer, "sqlite")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )


class IdMixin:
    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)


# ===== 状态常量 =====

# 用户
class UserStatus:
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    DISABLED = "DISABLED"
    PENDING_REVIEW = "PENDING_REVIEW"


# 邀请码
class InviteStatus:
    UNUSED = "UNUSED"
    USED = "USED"
    DISABLED = "DISABLED"
    EXPIRED = "EXPIRED"


# 会员
class MembershipStatus:
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"


# 订单
class OrderType:
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus:
    CREATED = "CREATED"
    WAITING_PAYMENT = "WAITING_PAYMENT"
    PAID = "PAID"
    WAITING_MATCH = "WAITING_MATCH"
    PARTIAL_MATCHED = "PARTIAL_MATCHED"
    FULL_MATCHED = "FULL_MATCHED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    DISPUTED = "DISPUTED"
    RISK_REVIEW = "RISK_REVIEW"


# 撮合
class MatchStatus:
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    CANCELLED = "CANCELLED"


class MatchOrderStatus:
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# 提现
class WithdrawalStatus:
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


# 工单
class TicketStatus:
    OPEN = "OPEN"
    PROCESSING = "PROCESSING"
    WAITING_USER = "WAITING_USER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# 申诉
class AppealStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


# 风控
class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskAction:
    ALLOW = "ALLOW"
    VERIFY = "VERIFY"
    REVIEW = "REVIEW"
    FREEZE = "FREEZE"
    BLOCK = "BLOCK"


# 流水方向
class TransactionDirection:
    IN = "IN"
    OUT = "OUT"


class BusinessType:
    ORDER_PAYMENT = "ORDER_PAYMENT"
    ORDER_SETTLEMENT = "ORDER_SETTLEMENT"
    SERVICE_FEE = "SERVICE_FEE"
    REFUND = "REFUND"
    WITHDRAWAL = "WITHDRAWAL"
    ADJUSTMENT = "ADJUSTMENT"
    PROMOTION_REWARD = "PROMOTION_REWARD"


# 通知
class NotificationType:
    ORDER = "ORDER"
    MATCH = "MATCH"
    PAYMENT = "PAYMENT"
    WITHDRAWAL = "WITHDRAWAL"
    TICKET = "TICKET"
    SYSTEM = "SYSTEM"
    RISK = "RISK"


class NotificationStatus:
    UNREAD = "UNREAD"
    READ = "READ"
