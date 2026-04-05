# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the cloudflare_email_routing module.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_email_routing,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    AnsibleExitJson,
    AnsibleFailJson,
    mock_cloudflare_client,
    set_module_args,
)

__all__ = [
    'test_missing_params',
    'test_enable_already_enabled',
    'test_enable_when_disabled',
    'test_disable_when_enabled',
    'test_enable_check_mode',
    'test_get_email_routing',
    'test_enable_email_routing',
    'test_disable_email_routing',
]

SETTINGS_ENABLED: dict[str, Any] = {
    'id': 'settings-id',
    'enabled': True,
    'name': 'example.com',
    'status': 'ready',
}

SETTINGS_DISABLED: dict[str, Any] = {
    'id': 'settings-id',
    'enabled': False,
    'name': 'example.com',
    'status': 'unconfigured',
}

ARGS: dict[str, Any] = {
    'zone_id': 'zone-id-123',
    'api_token': 'test-token',
    'enabled': True,
}


@pytest.mark.parametrize(
    'args',
    [
        {},
        {'zone_id': 'z', 'api_token': 't'},
        {'enabled': True, 'api_token': 't'},
    ],
)
def test_missing_params(args: dict[str, Any]) -> None:
    """Module fails with incomplete parameters."""
    with set_module_args(args):
        with pytest.raises(AnsibleFailJson):
            cloudflare_email_routing.main()


def test_enable_already_enabled(email_routing_mock: MagicMock) -> None:
    """Already enabled — no change."""
    with set_module_args(dict(ARGS)):
        email_routing_mock.get.return_value = {'result': SETTINGS_ENABLED}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing.main()
    assert exc.value.result['changed'] is False
    assert exc.value.result['email_routing']['enabled'] is True
    email_routing_mock.post.assert_not_called()


def test_enable_when_disabled(email_routing_mock: MagicMock) -> None:
    """Disabled — enable it."""
    with set_module_args(dict(ARGS)):
        email_routing_mock.get.return_value = {'result': SETTINGS_DISABLED}
        email_routing_mock.post.return_value = {'result': SETTINGS_ENABLED}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing.main()
    assert exc.value.result['changed'] is True
    email_routing_mock.post.assert_called_once_with(
        '/zones/zone-id-123/email/routing/enable',
    )


def test_disable_when_enabled(email_routing_mock: MagicMock) -> None:
    """Enabled — disable it."""
    with set_module_args({
        'zone_id': 'zone-id-123',
        'api_token': 'test-token',
        'enabled': False,
    }):
        email_routing_mock.get.return_value = {'result': SETTINGS_ENABLED}
        email_routing_mock.post.return_value = {'result': SETTINGS_DISABLED}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing.main()
    assert exc.value.result['changed'] is True
    email_routing_mock.post.assert_called_once_with(
        '/zones/zone-id-123/email/routing/disable',
    )


def test_enable_check_mode(email_routing_mock: MagicMock) -> None:
    """Check mode — changed=True, no POST."""
    with set_module_args({
        'zone_id': 'zone-id-123',
        'api_token': 'test-token',
        'enabled': True,
        '_ansible_check_mode': True,
    }):
        email_routing_mock.get.return_value = {'result': SETTINGS_DISABLED}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing.main()
    assert exc.value.result['changed'] is True
    email_routing_mock.post.assert_not_called()


def test_get_email_routing() -> None:
    """cloudflare_get_email_routing returns settings."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': SETTINGS_ENABLED}
    result = cloudflare_email_routing.cloudflare_get_email_routing(
        client,
        'zone-id-123',
    )
    assert result['enabled'] is True
    client.get.assert_called_once_with('/zones/zone-id-123/email/routing')


def test_enable_email_routing() -> None:
    """cloudflare_enable_email_routing calls enable endpoint."""
    client = mock_cloudflare_client()
    client.post.return_value = {'result': SETTINGS_ENABLED}
    result = cloudflare_email_routing.cloudflare_enable_email_routing(
        client,
        'zone-id-123',
    )
    assert result['enabled'] is True
    client.post.assert_called_once_with(
        '/zones/zone-id-123/email/routing/enable',
    )


def test_disable_email_routing() -> None:
    """cloudflare_disable_email_routing calls disable endpoint."""
    client = mock_cloudflare_client()
    client.post.return_value = {'result': SETTINGS_DISABLED}
    result = cloudflare_email_routing.cloudflare_disable_email_routing(
        client,
        'zone-id-123',
    )
    assert result['enabled'] is False
    client.post.assert_called_once_with(
        '/zones/zone-id-123/email/routing/disable',
    )
