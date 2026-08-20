"""生产环境密钥校验（G-03）。"""

from __future__ import annotations

import pytest


def test_production_placeholder_keys_rejected(monkeypatch):
    """APP_ENV=production + 占位密钥 → 拒绝启动。"""
    from app.config import settings
    from app.main import _validate_runtime_settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(RuntimeError) as exc:
        _validate_runtime_settings()
    assert "生产环境禁止使用默认/占位密钥" in str(exc.value)
    assert "JWT_SECRET" in str(exc.value)


def test_production_real_keys_pass(monkeypatch):
    """APP_ENV=production + 真实密钥 → 通过校验。"""
    from app.config import settings
    from app.main import _validate_runtime_settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "JWT_SECRET", "prod-9f8e7d6c5b4a")
    monkeypatch.setattr(settings, "SECRET_KEY", "prod-1a2b3c4d5e6f")
    monkeypatch.setattr(settings, "MYSQL_PASSWORD", "prod-db-pass-xyz")
    monkeypatch.setattr(settings, "RABBITMQ_PASSWORD", "prod-mq-pass-xyz")
    monkeypatch.setattr(settings, "ADMIN_INIT_PASSWORD", "prod-AdminPass@2026")

    _validate_runtime_settings()


def test_dev_skips_validation(monkeypatch):
    """非生产环境不校验占位密钥。"""
    from app.config import settings
    from app.main import _validate_runtime_settings

    monkeypatch.setattr(settings, "APP_ENV", "development")
    _validate_runtime_settings()
