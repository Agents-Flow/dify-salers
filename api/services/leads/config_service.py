"""
Leads configuration service.
Manages tenant-specific configuration for the leads module including API keys,
proxy settings, browser providers, and notification preferences.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.helper import encrypter
from extensions.ext_database import db
from models.leads import LeadsConfig, LeadsConfigKey

logger = logging.getLogger(__name__)


class LeadsConfigService:
    """Service for managing leads module configuration."""

    ENCRYPTED_KEYS = {
        LeadsConfigKey.APIFY_API_KEY,
        LeadsConfigKey.BROWSER_CREDENTIALS,
    }

    @staticmethod
    def get_config(tenant_id: str, config_key: str) -> dict[str, Any] | None:
        """Get a specific configuration value for a tenant."""
        with Session(db.engine) as session:
            stmt = select(LeadsConfig).where(
                LeadsConfig.tenant_id == tenant_id,
                LeadsConfig.config_key == config_key,
            )
            config = session.scalar(stmt)

            if not config:
                return None

            value = config.config_value

            if config.is_encrypted and isinstance(value, dict):
                value = LeadsConfigService._decrypt_config(value)

            return value

    @staticmethod
    def set_config(
        tenant_id: str,
        config_key: str,
        config_value: dict[str, Any],
        created_by: str | None = None,
    ) -> LeadsConfig:
        """Set a configuration value for a tenant."""
        should_encrypt = config_key in LeadsConfigService.ENCRYPTED_KEYS

        with Session(db.engine) as session:
            stmt = select(LeadsConfig).where(
                LeadsConfig.tenant_id == tenant_id,
                LeadsConfig.config_key == config_key,
            )
            config = session.scalar(stmt)

            if should_encrypt:
                stored_value = LeadsConfigService._encrypt_config(config_value)
            else:
                stored_value = config_value

            if config:
                config.config_value = stored_value
                config.is_encrypted = should_encrypt
            else:
                config = LeadsConfig(
                    tenant_id=tenant_id,
                    config_key=config_key,
                    config_value=stored_value,
                    is_encrypted=should_encrypt,
                )
                session.add(config)

            session.commit()
            session.refresh(config)
            return config

    @staticmethod
    def get_all_configs(tenant_id: str) -> dict[str, dict[str, Any]]:
        """Get all configuration values for a tenant."""
        with Session(db.engine) as session:
            stmt = select(LeadsConfig).where(LeadsConfig.tenant_id == tenant_id)
            configs = session.scalars(stmt).all()

            result = {}
            for config in configs:
                value = config.config_value
                if config.is_encrypted and isinstance(value, dict):
                    value = LeadsConfigService._mask_sensitive_config(value)
                result[config.config_key] = value

            return result

    @staticmethod
    def delete_config(tenant_id: str, config_key: str) -> bool:
        """Delete a configuration value for a tenant."""
        with Session(db.engine) as session:
            stmt = select(LeadsConfig).where(
                LeadsConfig.tenant_id == tenant_id,
                LeadsConfig.config_key == config_key,
            )
            config = session.scalar(stmt)

            if not config:
                return False

            session.delete(config)
            session.commit()
            return True

    @staticmethod
    def test_apify_connection(tenant_id: str) -> dict[str, Any]:
        """Test the Apify API connection using stored credentials."""
        config = LeadsConfigService.get_config(tenant_id, LeadsConfigKey.APIFY_API_KEY)

        if not config or not config.get("api_key"):
            return {"success": False, "message": "Apify API key not configured"}

        try:
            import httpx

            api_key = config["api_key"]
            response = httpx.get(
                "https://api.apify.com/v2/users/me",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                user_data = response.json().get("data", {})
                return {
                    "success": True,
                    "message": "Connection successful",
                    "username": user_data.get("username"),
                }
            return {"success": False, "message": f"API returned status {response.status_code}"}
        except Exception as e:
            logger.exception("Apify connection test failed")
            return {"success": False, "message": f"Connection failed: {e!s}"}

    @staticmethod
    def _encrypt_config(value: dict[str, Any]) -> dict[str, Any]:
        """Encrypt sensitive fields in config value."""
        encrypted = {}
        for key, val in value.items():
            if isinstance(val, str) and val:
                encrypted[key] = encrypter.encrypt_token(val)
            else:
                encrypted[key] = val
        return encrypted

    @staticmethod
    def _decrypt_config(value: dict[str, Any]) -> dict[str, Any]:
        """Decrypt sensitive fields in config value."""
        decrypted = {}
        for key, val in value.items():
            if isinstance(val, str) and val:
                try:
                    decrypted[key] = encrypter.decrypt_token(val)
                except Exception:
                    decrypted[key] = val
            else:
                decrypted[key] = val
        return decrypted

    @staticmethod
    def _mask_sensitive_config(value: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive fields for display purposes."""
        masked = {}
        for key, val in value.items():
            if isinstance(val, str) and len(val) > 4:
                masked[key] = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
            else:
                masked[key] = val
        return masked

    @staticmethod
    def get_config_schema() -> dict[str, dict[str, Any]]:
        """Get the schema for all configuration keys."""
        return {
            LeadsConfigKey.APIFY_API_KEY: {
                "label": "Apify API Key",
                "description": "API key for Apify scraping service",
                "is_encrypted": True,
                "fields": [{"name": "api_key", "type": "password", "required": True}],
            },
            LeadsConfigKey.PROXY_POOL_SETTINGS: {
                "label": "Proxy Pool Settings",
                "description": "Configuration for rotating proxies",
                "is_encrypted": False,
                "fields": [
                    {"name": "provider", "type": "select", "options": ["brightdata", "oxylabs", "smartproxy"]},
                    {"name": "pool_size", "type": "number", "default": 10},
                    {"name": "rotation_interval", "type": "number", "default": 300},
                ],
            },
            LeadsConfigKey.BROWSER_PROVIDER: {
                "label": "Browser Provider",
                "description": "Anti-detect browser service provider",
                "is_encrypted": False,
                "fields": [
                    {"name": "provider", "type": "select", "options": ["multilogin", "gologin", "adspower"]},
                ],
            },
            LeadsConfigKey.BROWSER_CREDENTIALS: {
                "label": "Browser Credentials",
                "description": "Login credentials for browser provider",
                "is_encrypted": True,
                "fields": [
                    {"name": "email", "type": "text", "required": True},
                    {"name": "password", "type": "password", "required": True},
                    {"name": "api_key", "type": "password"},
                ],
            },
            LeadsConfigKey.NOTIFICATION_SETTINGS: {
                "label": "Notification Settings",
                "description": "Configure how to receive notifications",
                "is_encrypted": False,
                "fields": [
                    {"name": "email_enabled", "type": "boolean", "default": False},
                    {"name": "email_address", "type": "email"},
                    {"name": "webhook_enabled", "type": "boolean", "default": False},
                    {"name": "webhook_url", "type": "url"},
                ],
            },
            LeadsConfigKey.DEFAULT_MESSAGE_TEMPLATES: {
                "label": "Default Message Templates",
                "description": "Default Spintax templates for DM messages",
                "is_encrypted": False,
                "fields": [
                    {"name": "greeting", "type": "textarea"},
                    {"name": "followup", "type": "textarea"},
                    {"name": "conversion", "type": "textarea"},
                ],
            },
        }
