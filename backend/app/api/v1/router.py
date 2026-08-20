"""API v1 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    admin,
    auth,
    banners,
    credit,
    finance,
    invites,
    orders,
    reservations,
    support,
    upload,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(invites.router)
api_router.include_router(credit.router)
api_router.include_router(orders.router)
api_router.include_router(reservations.router)
api_router.include_router(accounts.router)
api_router.include_router(finance.router)
api_router.include_router(support.router)
api_router.include_router(upload.router)
api_router.include_router(banners.router)
api_router.include_router(admin.router)
