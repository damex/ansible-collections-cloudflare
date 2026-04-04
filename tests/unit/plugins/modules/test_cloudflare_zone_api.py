# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for cloudflare_zone helper functions and client construction.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    cloudflare_create_client,
)
from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_zone,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    ACCOUNT,
    UNIVERSAL_SSL_DISABLED,
    UNIVERSAL_SSL_ENABLED,
    ZONE,
    mock_cloudflare_client,
)

__all__ = [
    'test_get_zone_found',
    'test_get_zone_not_found',
    'test_get_account_found',
    'test_get_account_not_found',
    'test_create_zone_payload',
    'test_delete_zone_endpoint',
    'test_get_zone_setting_returns_value',
    'test_set_zone_setting_sends_patch',
    'test_get_universal_ssl_returns_bool',
    'test_set_universal_ssl_sends_patch',
    'test_ensure_zone_setting_changed',
    'test_ensure_zone_setting_no_change',
    'test_ensure_zone_setting_check_mode',
    'test_ensure_universal_ssl_changed',
    'test_ensure_universal_ssl_no_change',
    'test_ensure_universal_ssl_check_mode',
    'test_token_auth_constructor',
    'test_legacy_auth_constructor',
]


def test_get_zone_found() -> None:
    """cloudflare_get_zone returns the zone dict when found."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': [ZONE]}
    result = cloudflare_zone.cloudflare_get_zone(client, 'example.com')
    assert result is not None
    assert result['name'] == 'example.com'
    client.get.assert_called_once_with(
        '/zones',
        params={'name': 'example.com'},
    )


def test_get_zone_not_found() -> None:
    """cloudflare_get_zone returns None when the zone does not exist."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': []}
    result = cloudflare_zone.cloudflare_get_zone(client, 'example.com')
    assert result is None


def test_get_account_found() -> None:
    """cloudflare_get_account returns the account dict when found."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': [ACCOUNT]}
    result = cloudflare_zone.cloudflare_get_account(client, 'my-account')
    assert result is not None
    assert result['id'] == 'acct-id-456'
    client.get.assert_called_once_with(
        '/accounts',
        params={'name': 'my-account'},
    )


def test_get_account_not_found() -> None:
    """cloudflare_get_account returns None when the account does not exist."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': []}
    result = cloudflare_zone.cloudflare_get_account(client, 'missing')
    assert result is None


def test_create_zone_payload() -> None:
    """cloudflare_create_zone sends the correct POST payload."""
    client = mock_cloudflare_client()
    client.post.return_value = {'result': ZONE}
    cloudflare_zone.cloudflare_create_zone(
        client,
        'example.com',
        'acct-id-456',
        jump_start=True,
        zone_type='partial',
    )
    client.post.assert_called_once_with(
        '/zones',
        data={
            'name': 'example.com',
            'account': {'id': 'acct-id-456'},
            'jump_start': True,
            'type': 'partial',
        },
    )


def test_delete_zone_endpoint() -> None:
    """cloudflare_delete_zone calls delete with the correct zone ID."""
    client = mock_cloudflare_client()
    client.delete.return_value = {'result': {'id': 'zone-id-123'}}
    cloudflare_zone.cloudflare_delete_zone(client, 'zone-id-123')
    client.delete.assert_called_once_with('/zones/zone-id-123')


def test_get_zone_setting_returns_value() -> None:
    """cloudflare_get_zone_setting extracts the value field from the settings response."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': {'id': 'ssl', 'value': 'full'}}
    result = cloudflare_zone.cloudflare_get_zone_setting(client, 'zone-id-123', 'ssl')
    assert result == 'full'
    client.get.assert_called_once_with('/zones/zone-id-123/settings/ssl')


def test_set_zone_setting_sends_patch() -> None:
    """cloudflare_set_zone_setting sends PATCH with the correct value payload."""
    client = mock_cloudflare_client()
    client.patch.return_value = {'result': {'id': 'ssl', 'value': 'strict'}}
    cloudflare_zone.cloudflare_set_zone_setting(client, 'zone-id-123', 'ssl', 'strict')
    client.patch.assert_called_once_with(
        '/zones/zone-id-123/settings/ssl',
        data={'value': 'strict'},
    )


def test_get_universal_ssl_returns_bool() -> None:
    """cloudflare_get_universal_ssl extracts the enabled field from the response."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': UNIVERSAL_SSL_ENABLED}
    result = cloudflare_zone.cloudflare_get_universal_ssl(client, 'zone-id-123')
    assert result is True
    client.get.assert_called_once_with('/zones/zone-id-123/ssl/universal/settings')


def test_set_universal_ssl_sends_patch() -> None:
    """cloudflare_set_universal_ssl sends PATCH with the correct enabled payload."""
    client = mock_cloudflare_client()
    client.patch.return_value = {'result': UNIVERSAL_SSL_DISABLED}
    cloudflare_zone.cloudflare_set_universal_ssl(client, 'zone-id-123', False)
    client.patch.assert_called_once_with(
        '/zones/zone-id-123/ssl/universal/settings',
        data={'enabled': False},
    )


def test_ensure_zone_setting_changed() -> None:
    """cloudflare_ensure_zone_setting returns True and patches when value differs."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': {'id': 'ssl', 'value': 'flexible'}}
    client.patch.return_value = {'result': {'id': 'ssl', 'value': 'full'}}
    result = cloudflare_zone.cloudflare_ensure_zone_setting(
        client,
        'zone-id-123',
        'ssl',
        'full',
        False,
    )
    assert result is True
    client.patch.assert_called_once_with(
        '/zones/zone-id-123/settings/ssl',
        data={'value': 'full'},
    )


def test_ensure_zone_setting_no_change() -> None:
    """cloudflare_ensure_zone_setting returns False and skips patch when value matches."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': {'id': 'ssl', 'value': 'full'}}
    result = cloudflare_zone.cloudflare_ensure_zone_setting(
        client,
        'zone-id-123',
        'ssl',
        'full',
        False,
    )
    assert result is False
    client.patch.assert_not_called()


def test_ensure_zone_setting_check_mode() -> None:
    """cloudflare_ensure_zone_setting returns True but skips patch in check mode."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': {'id': 'ssl', 'value': 'flexible'}}
    result = cloudflare_zone.cloudflare_ensure_zone_setting(
        client,
        'zone-id-123',
        'ssl',
        'full',
        True,
    )
    assert result is True
    client.patch.assert_not_called()


def test_ensure_universal_ssl_changed() -> None:
    """cloudflare_ensure_universal_ssl returns True and patches when enabled differs."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': UNIVERSAL_SSL_DISABLED}
    client.patch.return_value = {'result': UNIVERSAL_SSL_ENABLED}
    result = cloudflare_zone.cloudflare_ensure_universal_ssl(
        client,
        'zone-id-123',
        True,
        False,
    )
    assert result is True
    client.patch.assert_called_once_with(
        '/zones/zone-id-123/ssl/universal/settings',
        data={'enabled': True},
    )


def test_ensure_universal_ssl_no_change() -> None:
    """cloudflare_ensure_universal_ssl returns False and skips patch when enabled matches."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': UNIVERSAL_SSL_ENABLED}
    result = cloudflare_zone.cloudflare_ensure_universal_ssl(
        client,
        'zone-id-123',
        True,
        False,
    )
    assert result is False
    client.patch.assert_not_called()


def test_ensure_universal_ssl_check_mode() -> None:
    """cloudflare_ensure_universal_ssl returns True but skips patch in check mode."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': UNIVERSAL_SSL_DISABLED}
    result = cloudflare_zone.cloudflare_ensure_universal_ssl(
        client,
        'zone-id-123',
        True,
        True,
    )
    assert result is True
    client.patch.assert_not_called()


def test_token_auth_constructor() -> None:
    """API token auth creates client with token parameter."""
    module = MagicMock()
    module.params = {
        'api_token': 'my-token',
        'account_email': None,
        'account_api_key': None,
    }
    client = cloudflare_create_client(module)
    assert client.parameters.api_token == 'my-token'
    assert client.parameters.account_email is None
    assert client.parameters.account_api_key is None


def test_legacy_auth_constructor() -> None:
    """Legacy auth creates client with email and key parameters."""
    module = MagicMock()
    module.params = {
        'api_token': None,
        'account_email': 'user@example.com',
        'account_api_key': 'legacy-key',
    }
    client = cloudflare_create_client(module)
    assert client.parameters.api_token is None
    assert client.parameters.account_email == 'user@example.com'
    assert client.parameters.account_api_key == 'legacy-key'
