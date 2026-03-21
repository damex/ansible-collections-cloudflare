# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the CloudflareAPI utility class.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_zone,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    ACCOUNT,
    UNIVERSAL_SSL_DISABLED,
    UNIVERSAL_SSL_ENABLED,
    ZONE,
    CFMock,
)

__all__ = [
    "test_get_zone_found",
    "test_get_zone_not_found",
    "test_get_account_found",
    "test_get_account_not_found",
    "test_create_zone_payload",
    "test_delete_zone_endpoint",
    "test_get_zone_setting_returns_value",
    "test_set_zone_setting_sends_patch",
    "test_get_universal_ssl_returns_bool",
    "test_set_universal_ssl_sends_patch",
    "test_ensure_zone_setting_changed",
    "test_ensure_zone_setting_no_change",
    "test_ensure_zone_setting_check_mode",
    "test_ensure_universal_ssl_changed",
    "test_ensure_universal_ssl_no_change",
    "test_ensure_universal_ssl_check_mode",
    "test_token_auth_constructor",
    "test_legacy_auth_constructor",
]


class AnsibleFailJson(Exception):
    """
    Raised by mocked fail_json.

    >>> raise AnsibleFailJson({"msg": "error"})
    Traceback (most recent call last):
        ...
    test_cloudflare_zone_api.AnsibleFailJson: {'msg': 'error'}
    """

    def __init__(self, result: dict[str, Any]) -> None:
        """
        Store result for assertion.

        >>> AnsibleFailJson({"msg": "error"}).result
        {'msg': 'error'}
        """
        super().__init__(result)
        self.result = result


def _raise_fail_json(msg: str) -> None:
    """
    Raise AnsibleFailJson with the error message.

    >>> _raise_fail_json("not found")
    Traceback (most recent call last):
        ...
    test_cloudflare_zone_api.AnsibleFailJson: {'msg': 'not found'}
    """
    raise AnsibleFailJson({"msg": msg})


def make_module(api_token: str) -> MagicMock:
    """
    Build a mock AnsibleModule for CloudflareAPI instantiation.

    >>> make_module(api_token="t").params["api_token"]
    't'
    """
    module = MagicMock()
    module.params = {
        "api_token": api_token,
        "account_email": None,
        "account_api_key": None,
    }
    module.check_mode = False
    module.fail_json.side_effect = _raise_fail_json
    return module


def test_get_zone_found(cf_mock: CFMock) -> None:
    """get_zone returns the zone dict when found."""
    cf_mock.client.zones.get.return_value = [ZONE]
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.get_zone("example.com")
    assert result is not None
    assert result["name"] == "example.com"
    cf_mock.client.zones.get.assert_called_once_with(params={"name": "example.com"})


def test_get_zone_not_found(cf_mock: CFMock) -> None:
    """get_zone returns None when the zone does not exist."""
    cf_mock.client.zones.get.return_value = []
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.get_zone("example.com")
    assert result is None


def test_get_account_found(cf_mock: CFMock) -> None:
    """get_account returns the account dict when found."""
    cf_mock.client.accounts.get.return_value = [ACCOUNT]
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.get_account("my-account")
    assert result is not None
    assert result["id"] == "acct-id-456"
    cf_mock.client.accounts.get.assert_called_once_with(params={"name": "my-account"})


def test_get_account_not_found(cf_mock: CFMock) -> None:
    """get_account returns None when the account does not exist."""
    cf_mock.client.accounts.get.return_value = []
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.get_account("missing")
    assert result is None


def test_create_zone_payload(cf_mock: CFMock) -> None:
    """create_zone sends the correct POST payload."""
    cf_mock.client.zones.post.return_value = ZONE
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    api.create_zone(
        "example.com",
        "acct-id-456",
        jump_start=True,
        zone_type="partial",
    )
    cf_mock.client.zones.post.assert_called_once_with(
        data={
            "name": "example.com",
            "account": {"id": "acct-id-456"},
            "jump_start": True,
            "type": "partial",
        },
    )


def test_delete_zone_endpoint(cf_mock: CFMock) -> None:
    """delete_zone calls delete on the client with the correct zone ID."""
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    api.delete_zone("zone-id-123")
    cf_mock.client.zones.delete.assert_called_once_with("zone-id-123")


def test_get_zone_setting_returns_value(cf_mock: CFMock) -> None:
    """get_zone_setting extracts the value field from the settings response."""
    cf_mock.client.zones.settings.ssl.get.return_value = {"id": "ssl", "value": "full"}
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.get_zone_setting("zone-id-123", "ssl")
    assert result == "full"
    cf_mock.client.zones.settings.ssl.get.assert_called_once_with("zone-id-123")


def test_set_zone_setting_sends_patch(cf_mock: CFMock) -> None:
    """set_zone_setting sends PATCH with the correct value payload."""
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    api.set_zone_setting("zone-id-123", "ssl", "strict")
    cf_mock.client.zones.settings.ssl.patch.assert_called_once_with(
        "zone-id-123",
        data={"value": "strict"},
    )


def test_get_universal_ssl_returns_bool(cf_mock: CFMock) -> None:
    """get_universal_ssl extracts the enabled field from the response."""
    cf_mock.client.zones.ssl.universal.settings.get.return_value = UNIVERSAL_SSL_ENABLED
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.get_universal_ssl("zone-id-123")
    assert result is True
    cf_mock.client.zones.ssl.universal.settings.get.assert_called_once_with("zone-id-123")


def test_set_universal_ssl_sends_patch(cf_mock: CFMock) -> None:
    """set_universal_ssl sends PATCH with the correct enabled payload."""
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    api.set_universal_ssl("zone-id-123", False)
    cf_mock.client.zones.ssl.universal.settings.patch.assert_called_once_with(
        "zone-id-123",
        data={"enabled": False},
    )


def test_ensure_zone_setting_changed(cf_mock: CFMock) -> None:
    """ensure_zone_setting returns True and patches when value differs."""
    cf_mock.client.zones.settings.ssl.get.return_value = {"id": "ssl", "value": "flexible"}
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.ensure_zone_setting("zone-id-123", "ssl", "full")
    assert result is True
    cf_mock.client.zones.settings.ssl.patch.assert_called_once_with(
        "zone-id-123",
        data={"value": "full"},
    )


def test_ensure_zone_setting_no_change(cf_mock: CFMock) -> None:
    """ensure_zone_setting returns False and skips patch when value matches."""
    cf_mock.client.zones.settings.ssl.get.return_value = {"id": "ssl", "value": "full"}
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.ensure_zone_setting("zone-id-123", "ssl", "full")
    assert result is False
    cf_mock.client.zones.settings.ssl.patch.assert_not_called()


def test_ensure_zone_setting_check_mode(cf_mock: CFMock) -> None:
    """ensure_zone_setting returns True but skips patch in check mode."""
    cf_mock.client.zones.settings.ssl.get.return_value = {"id": "ssl", "value": "flexible"}
    module = make_module(api_token="t")
    module.check_mode = True
    api = cloudflare_zone.CloudflareAPI(module)
    result = api.ensure_zone_setting("zone-id-123", "ssl", "full")
    assert result is True
    cf_mock.client.zones.settings.ssl.patch.assert_not_called()


def test_ensure_universal_ssl_changed(cf_mock: CFMock) -> None:
    """ensure_universal_ssl returns True and patches when enabled differs."""
    cf_mock.client.zones.ssl.universal.settings.get.return_value = UNIVERSAL_SSL_DISABLED
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.ensure_universal_ssl("zone-id-123", True)
    assert result is True
    cf_mock.client.zones.ssl.universal.settings.patch.assert_called_once_with(
        "zone-id-123",
        data={"enabled": True},
    )


def test_ensure_universal_ssl_no_change(cf_mock: CFMock) -> None:
    """ensure_universal_ssl returns False and skips patch when enabled matches."""
    cf_mock.client.zones.ssl.universal.settings.get.return_value = UNIVERSAL_SSL_ENABLED
    api = cloudflare_zone.CloudflareAPI(make_module(api_token="t"))
    result = api.ensure_universal_ssl("zone-id-123", True)
    assert result is False
    cf_mock.client.zones.ssl.universal.settings.patch.assert_not_called()


def test_ensure_universal_ssl_check_mode(cf_mock: CFMock) -> None:
    """ensure_universal_ssl returns True but skips patch in check mode."""
    cf_mock.client.zones.ssl.universal.settings.get.return_value = UNIVERSAL_SSL_DISABLED
    module = make_module(api_token="t")
    module.check_mode = True
    api = cloudflare_zone.CloudflareAPI(module)
    result = api.ensure_universal_ssl("zone-id-123", True)
    assert result is True
    cf_mock.client.zones.ssl.universal.settings.patch.assert_not_called()


def test_token_auth_constructor(cf_mock: CFMock) -> None:
    """API token auth passes token to CloudFlare constructor."""
    cloudflare_zone.CloudflareAPI(make_module(api_token="my-token"))
    cf_mock.cls.assert_called_once_with(token="my-token")


def test_legacy_auth_constructor(cf_mock: CFMock) -> None:
    """Legacy auth passes email and key to CloudFlare constructor."""
    module = MagicMock()
    module.params = {
        "api_token": None,
        "account_email": "user@example.com",
        "account_api_key": "legacy-key",
    }
    cloudflare_zone.CloudflareAPI(module)
    cf_mock.cls.assert_called_once_with(
        email="user@example.com",
        key="legacy-key",
    )
