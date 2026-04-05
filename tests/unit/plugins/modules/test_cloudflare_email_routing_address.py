# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the cloudflare_email_routing_address module.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_email_routing_address,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    AnsibleExitJson,
    AnsibleFailJson,
    mock_cloudflare_client,
    set_module_args,
)

__all__ = [
    'test_missing_params',
    'test_present_address_exists',
    'test_present_address_created',
    'test_present_check_mode',
    'test_absent_address_exists',
    'test_absent_address_missing',
    'test_absent_check_mode',
    'test_find_address_found',
    'test_find_address_not_found',
    'test_create_address_payload',
    'test_delete_address_endpoint',
]

ADDRESS: dict[str, Any] = {
    'id': 'addr-id-123',
    'email': 'user@gmail.com',
    'verified': '2024-01-01T00:00:00Z',
    'created': '2024-01-01T00:00:00Z',
    'modified': '2024-01-01T00:00:00Z',
}

ARGS: dict[str, str] = {
    'email': 'user@gmail.com',
    'account_id': 'acct-id-456',
    'api_token': 'test-token',
}


@pytest.mark.parametrize(
    'args',
    [
        {},
        {'email': 'u@e.com', 'api_token': 't'},
        {'account_id': 'a', 'api_token': 't'},
    ],
)
def test_missing_params(args: dict[str, Any]) -> None:
    """Module fails with incomplete parameters."""
    with set_module_args(args):
        with pytest.raises(AnsibleFailJson):
            cloudflare_email_routing_address.main()


def test_present_address_exists(address_mock: MagicMock) -> None:
    """Existing address — no change."""
    with set_module_args(dict(ARGS)):
        address_mock.get.return_value = {'result': [ADDRESS]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_address.main()
    assert exc.value.result['changed'] is False
    assert exc.value.result['address']['email'] == 'user@gmail.com'


def test_present_address_created(address_mock: MagicMock) -> None:
    """Missing address — create it."""
    with set_module_args(dict(ARGS)):
        address_mock.get.return_value = {'result': []}
        address_mock.post.return_value = {'result': ADDRESS}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_address.main()
    assert exc.value.result['changed'] is True
    address_mock.post.assert_called_once_with(
        '/accounts/acct-id-456/email/routing/addresses',
        data={'email': 'user@gmail.com'},
    )


def test_present_check_mode(address_mock: MagicMock) -> None:
    """Check mode — changed=True, no POST."""
    with set_module_args({
        'email': 'user@gmail.com',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        '_ansible_check_mode': True,
    }):
        address_mock.get.return_value = {'result': []}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_address.main()
    assert exc.value.result['changed'] is True
    address_mock.post.assert_not_called()


def test_absent_address_exists(address_mock: MagicMock) -> None:
    """Address exists — delete it."""
    with set_module_args({
        'email': 'user@gmail.com',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'state': 'absent',
    }):
        address_mock.get.return_value = {'result': [ADDRESS]}
        address_mock.delete.return_value = {'result': {}}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_address.main()
    assert exc.value.result['changed'] is True
    address_mock.delete.assert_called_once_with(
        '/accounts/acct-id-456/email/routing/addresses/addr-id-123',
    )


def test_absent_address_missing(address_mock: MagicMock) -> None:
    """Address missing — no change."""
    with set_module_args({
        'email': 'user@gmail.com',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'state': 'absent',
    }):
        address_mock.get.return_value = {'result': []}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_address.main()
    assert exc.value.result['changed'] is False


def test_absent_check_mode(address_mock: MagicMock) -> None:
    """Check mode — changed=True, no DELETE."""
    with set_module_args({
        'email': 'user@gmail.com',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'state': 'absent',
        '_ansible_check_mode': True,
    }):
        address_mock.get.return_value = {'result': [ADDRESS]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_address.main()
    assert exc.value.result['changed'] is True
    address_mock.delete.assert_not_called()


def test_find_address_found() -> None:
    """cloudflare_find_email_routing_address returns address when found."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': [ADDRESS]}
    result = cloudflare_email_routing_address.cloudflare_find_email_routing_address(
        client,
        'acct-id-456',
        'user@gmail.com',
    )
    assert result is not None
    assert result['email'] == 'user@gmail.com'


def test_find_address_not_found() -> None:
    """cloudflare_find_email_routing_address returns None when not found."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': []}
    result = cloudflare_email_routing_address.cloudflare_find_email_routing_address(
        client,
        'acct-id-456',
        'missing@gmail.com',
    )
    assert result is None


def test_create_address_payload() -> None:
    """cloudflare_create_email_routing_address sends correct payload."""
    client = mock_cloudflare_client()
    client.post.return_value = {'result': ADDRESS}
    cloudflare_email_routing_address.cloudflare_create_email_routing_address(
        client,
        'acct-id-456',
        'user@gmail.com',
    )
    client.post.assert_called_once_with(
        '/accounts/acct-id-456/email/routing/addresses',
        data={'email': 'user@gmail.com'},
    )


def test_delete_address_endpoint() -> None:
    """cloudflare_delete_email_routing_address calls correct endpoint."""
    client = mock_cloudflare_client()
    client.delete.return_value = {'result': {}}
    cloudflare_email_routing_address.cloudflare_delete_email_routing_address(
        client,
        'acct-id-456',
        'addr-id-123',
    )
    client.delete.assert_called_once_with(
        '/accounts/acct-id-456/email/routing/addresses/addr-id-123',
    )
