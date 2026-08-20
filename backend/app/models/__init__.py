"""模型注册，确保 Alembic 与建表能发现全部表。"""

from app.models.account import Account, AccountTransaction
from app.models.admin import (
    AdminPermission,
    AdminRole,
    AdminRolePermission,
    AdminUser,
    AdminUserRole,
)
from app.models.appeal import Appeal, AppealLog
from app.models.audit import IdempotencyRecord, OperationLog, SystemConfig
from app.models.banner import Banner
from app.models.base import (
    AppealStatus,
    BusinessType,
    InviteStatus,
    MatchStatus,
    MembershipStatus,
    NotificationStatus,
    NotificationType,
    OrderStatus,
    OrderType,
    RiskAction,
    RiskLevel,
    TicketStatus,
    TransactionDirection,
    UserStatus,
    WithdrawalStatus,
)
from app.models.credit import CreditLevel
from app.models.fee import FeeRecord, FeeRule
from app.models.invite import InviteCode, UserRelation, UserRelationStat
from app.models.matching import MatchingJob, MatchLog, MatchOrder
from app.models.membership import Membership, MembershipLevel, MembershipOrder
from app.models.notification import Announcement, Notification
from app.models.order import (
    BuyOrder,
    Order,
    OrderStatusLog,
    SellOrder,
)
from app.models.promotion import PromotionRecord, PromotionRule
from app.models.reservation import ReservationOrder
from app.models.risk import RiskEvent, RiskRule, RiskUser
from app.models.support import SupportTicket, TicketMessage
from app.models.user import (
    User,
    UserDevice,
    UserLoginLog,
    UserProfile,
)
from app.models.withdrawal import WithdrawalLog, WithdrawalOrder

__all__ = [
    "Account",
    "AccountTransaction",
    "AdminPermission",
    "AdminRole",
    "AdminRolePermission",
    "AdminUser",
    "AdminUserRole",
    "Announcement",
    "Appeal",
    "AppealLog",
    "AppealStatus",
    "Banner",
    "BusinessType",
    "BuyOrder",
    "CreditLevel",
    "FeeRecord",
    "FeeRule",
    "IdempotencyRecord",
    "InviteCode",
    "InviteStatus",
    "MatchingJob",
    "MatchLog",
    "MatchOrder",
    "MatchStatus",
    "Membership",
    "MembershipLevel",
    "MembershipOrder",
    "MembershipStatus",
    "Notification",
    "NotificationStatus",
    "NotificationType",
    "OperationLog",
    "Order",
    "OrderStatus",
    "OrderStatusLog",
    "OrderType",
    "PromotionRecord",
    "PromotionRule",
    "ReservationOrder",
    "RiskAction",
    "RiskEvent",
    "RiskLevel",
    "RiskRule",
    "RiskUser",
    "SellOrder",
    "SupportTicket",
    "SystemConfig",
    "TicketMessage",
    "TicketStatus",
    "TransactionDirection",
    "User",
    "UserDevice",
    "UserLoginLog",
    "UserProfile",
    "UserRelation",
    "UserRelationStat",
    "UserStatus",
    "WithdrawalLog",
    "WithdrawalOrder",
    "WithdrawalStatus",
]
