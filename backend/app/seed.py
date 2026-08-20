"""初始化数据：超级管理员 / RBAC / 默认配置 / 示例商品。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.admin import AdminUser
from app.models.banner import Banner
from app.models.credit import CreditLevel
from app.models.fee import FeeRule
from app.models.notification import Announcement
from app.models.promotion import PromotionRule
from app.services import admin_service
from app.utils.misc import gen_code


async def init_super_admin(db: AsyncSession) -> None:
    from app.config import settings

    exists = await db.scalar(select(AdminUser).where(AdminUser.username == settings.ADMIN_INIT_USERNAME))
    if exists:
        return
    admin = AdminUser(
        username=settings.ADMIN_INIT_USERNAME,
        password_hash=hash_password(settings.ADMIN_INIT_PASSWORD),
        nickname="超级管理员",
        role_code="SUPER_ADMIN",
        is_super=True,
    )
    db.add(admin)
    await db.flush()


async def init_rbac(db: AsyncSession) -> None:
    await admin_service.seed_permissions(db)
    await admin_service.seed_system_roles(db)


async def init_configs(db: AsyncSession) -> None:
    fee = await db.scalar(select(FeeRule).where(FeeRule.fee_type == "ORDER_SERVICE_FEE"))
    if not fee:
        db.add(
            FeeRule(
                fee_type="ORDER_SERVICE_FEE",
                name="订单服务费",
                rate=Decimal("0.05"),
                min_fee=Decimal("0"),
                max_fee=Decimal("0"),
                status="ACTIVE",
            )
        )
    promo = await db.scalar(select(PromotionRule).where(PromotionRule.rule_type == "ORDER_COMMISSION"))
    if not promo:
        db.add(
            PromotionRule(
                rule_type="ORDER_COMMISSION",
                name="成交推广奖励",
                rate=Decimal("0.02"),
                status="ACTIVE",
            )
        )
    levels = await db.scalar(select(CreditLevel).limit(1))
    if not levels:
        db.add_all(
            [
                CreditLevel(name="普通信用", code="BASIC", min_orders=0, description="初始信用等级", sort_order=0),
                CreditLevel(name="铜牌信用", code="BRONZE", min_orders=3, description="累计完成 3 笔订单", sort_order=1),
                CreditLevel(name="银牌信用", code="SILVER", min_orders=10, description="累计完成 10 笔订单", sort_order=2),
                CreditLevel(name="金牌信用", code="GOLD", min_orders=30, description="累计完成 30 笔订单", sort_order=3),
                CreditLevel(name="钻石信用", code="DIAMOND", min_orders=80, description="累计完成 80 笔订单", sort_order=4),
            ]
        )
    if not await db.scalar(select(Announcement).limit(1)):
        db.add(Announcement(title="欢迎使用 LX 平台", content="本平台为会员互助订单撮合平台，支持提供援助（买入）与获得援助（卖出）订单。", type="NOTICE", status="ACTIVE"))


async def init_system_invites(db: AsyncSession) -> None:
    """系统初始邀请码，便于首批用户注册（creator_id 为空表示系统发放）。"""
    from app.models.invite import InviteCode

    count = await db.scalar(select(InviteCode).limit(1))
    if count:
        return
    for _ in range(10):
        db.add(InviteCode(code=gen_code(8), creator_id=None, status="ACTIVE"))


async def init_banners(db: AsyncSession) -> None:
    """示例首页轮播广告。"""
    count = await db.scalar(select(Banner).limit(1))
    if count:
        return
    db.add_all(
        [
            Banner(
                title="欢迎加入 LX 平台",
                subtitle="订单撮合 · 会员服务",
                link_type="NONE",
                sort_order=3,
                status="ACTIVE",
            ),
            Banner(
                title="提供援助（买入）",
                subtitle="先支付后撮合，快速获得服务",
                link_type="LINK",
                link_value="/aid-order?type=BUY",
                sort_order=2,
                status="ACTIVE",
            ),
            Banner(
                title="获得援助（卖出）",
                subtitle="发布需求，排队等待撮合",
                link_type="LINK",
                link_value="/aid-order?type=SELL",
                sort_order=1,
                status="ACTIVE",
            ),
        ]
    )


async def run_seed(db: AsyncSession) -> None:
    await init_super_admin(db)
    await init_rbac(db)
    await init_configs(db)
    await init_system_invites(db)
    await init_banners(db)
    await db.commit()
