# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the cloudflare_email_routing_rule module.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_email_routing_rule,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    AnsibleExitJson,
    AnsibleFailJson,
    mock_cloudflare_client,
    set_module_args,
)

__all__ = [
    'test_missing_params',
    'test_present_rule_exists_no_change',
    'test_present_rule_created',
    'test_present_rule_updated',
    'test_present_check_mode_create',
    'test_present_check_mode_update',
    'test_absent_rule_exists',
    'test_absent_rule_missing',
    'test_absent_check_mode',
    'test_find_rule_found',
    'test_find_rule_not_found',
    'test_create_rule_payload',
    'test_update_rule_payload',
    'test_delete_rule_endpoint',
]

CATCH_ALL_RULE: dict[str, Any] = {
    'id': 'rule-id-123',
    'name': 'catch-all',
    'enabled': True,
    'priority': 0,
    'matchers': [{'type': 'all'}],
    'actions': [{'type': 'forward', 'value': ['user@gmail.com']}],
}

ARGS: dict[str, Any] = {
    'name': 'catch-all',
    'zone_id': 'zone-id-123',
    'api_token': 'test-token',
    'matchers': [{'type': 'all'}],
    'actions': [{'type': 'forward', 'value': ['user@gmail.com']}],
}


@pytest.mark.parametrize(
    'args',
    [
        {},
        {'name': 'r', 'api_token': 't'},
        {'zone_id': 'z', 'api_token': 't'},
    ],
)
def test_missing_params(args: dict[str, Any]) -> None:
    """Module fails with incomplete parameters."""
    with set_module_args(args):
        with pytest.raises(AnsibleFailJson):
            cloudflare_email_routing_rule.main()


def test_present_rule_exists_no_change(rule_mock: MagicMock) -> None:
    """Existing rule with matching config — no change."""
    with set_module_args(dict(ARGS)):
        rule_mock.get.return_value = {'result': [CATCH_ALL_RULE]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_rule.main()
    assert exc.value.result['changed'] is False
    assert exc.value.result['rule']['name'] == 'catch-all'


def test_present_rule_created(rule_mock: MagicMock) -> None:
    """Missing rule — create it."""
    with set_module_args(dict(ARGS)):
        rule_mock.get.return_value = {'result': []}
        rule_mock.post.return_value = {'result': CATCH_ALL_RULE}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_rule.main()
    assert exc.value.result['changed'] is True
    rule_mock.post.assert_called_once()


def test_present_rule_updated(rule_mock: MagicMock) -> None:
    """Existing rule with different actions — update it."""
    updated_args = dict(ARGS)
    updated_args['actions'] = [{'type': 'forward', 'value': ['other@gmail.com']}]
    with set_module_args(updated_args):
        rule_mock.get.return_value = {'result': [CATCH_ALL_RULE]}
        updated_rule = dict(CATCH_ALL_RULE)
        updated_rule['actions'] = [{'type': 'forward', 'value': ['other@gmail.com']}]
        rule_mock.put.return_value = {'result': updated_rule}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_rule.main()
    assert exc.value.result['changed'] is True
    rule_mock.put.assert_called_once()


def test_present_check_mode_create(rule_mock: MagicMock) -> None:
    """Check mode for new rule — changed=True, no POST."""
    with set_module_args({
        'name': 'catch-all',
        'zone_id': 'zone-id-123',
        'api_token': 'test-token',
        'matchers': [{'type': 'all'}],
        'actions': [{'type': 'forward', 'value': ['user@gmail.com']}],
        '_ansible_check_mode': True,
    }):
        rule_mock.get.return_value = {'result': []}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_rule.main()
    assert exc.value.result['changed'] is True
    rule_mock.post.assert_not_called()


def test_present_check_mode_update(rule_mock: MagicMock) -> None:
    """Check mode for changed rule — changed=True, no PUT."""
    with set_module_args({
        'name': 'catch-all',
        'zone_id': 'zone-id-123',
        'api_token': 'test-token',
        'matchers': [{'type': 'all'}],
        'actions': [{'type': 'drop'}],
        '_ansible_check_mode': True,
    }):
        rule_mock.get.return_value = {'result': [CATCH_ALL_RULE]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_rule.main()
    assert exc.value.result['changed'] is True
    rule_mock.put.assert_not_called()


def test_absent_rule_exists(rule_mock: MagicMock) -> None:
    """Rule exists — delete it."""
    with set_module_args({
        'name': 'catch-all',
        'zone_id': 'zone-id-123',
        'api_token': 'test-token',
        'state': 'absent',
        'matchers': [{'type': 'all'}],
        'actions': [{'type': 'forward', 'value': ['user@gmail.com']}],
    }):
        rule_mock.get.return_value = {'result': [CATCH_ALL_RULE]}
        rule_mock.delete.return_value = {'result': {}}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_rule.main()
    assert exc.value.result['changed'] is True
    rule_mock.delete.assert_called_once_with(
        '/zones/zone-id-123/email/routing/rules/rule-id-123',
    )


def test_absent_rule_missing(rule_mock: MagicMock) -> None:
    """Rule missing — no change."""
    with set_module_args({
        'name': 'catch-all',
        'zone_id': 'zone-id-123',
        'api_token': 'test-token',
        'state': 'absent',
        'matchers': [{'type': 'all'}],
        'actions': [{'type': 'forward', 'value': ['user@gmail.com']}],
    }):
        rule_mock.get.return_value = {'result': []}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_rule.main()
    assert exc.value.result['changed'] is False


def test_absent_check_mode(rule_mock: MagicMock) -> None:
    """Check mode — changed=True, no DELETE."""
    with set_module_args({
        'name': 'catch-all',
        'zone_id': 'zone-id-123',
        'api_token': 'test-token',
        'state': 'absent',
        'matchers': [{'type': 'all'}],
        'actions': [{'type': 'forward', 'value': ['user@gmail.com']}],
        '_ansible_check_mode': True,
    }):
        rule_mock.get.return_value = {'result': [CATCH_ALL_RULE]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_email_routing_rule.main()
    assert exc.value.result['changed'] is True
    rule_mock.delete.assert_not_called()


def test_find_rule_found() -> None:
    """cloudflare_find_email_routing_rule returns rule when matchers match."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': [CATCH_ALL_RULE]}
    result = cloudflare_email_routing_rule.cloudflare_find_email_routing_rule(
        client,
        'zone-id-123',
        [{'type': 'all'}],
    )
    assert result is not None
    assert result['name'] == 'catch-all'


def test_find_rule_not_found() -> None:
    """cloudflare_find_email_routing_rule returns None when no matchers match."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': []}
    result = cloudflare_email_routing_rule.cloudflare_find_email_routing_rule(
        client,
        'zone-id-123',
        [{'type': 'literal', 'field': 'to', 'value': 'missing@example.com'}],
    )
    assert result is None


def test_create_rule_payload() -> None:
    """cloudflare_create_email_routing_rule sends correct payload."""
    client = mock_cloudflare_client()
    client.post.return_value = {'result': CATCH_ALL_RULE}
    data = {
        'name': 'catch-all',
        'enabled': True,
        'matchers': [{'type': 'all'}],
        'actions': [{'type': 'forward', 'value': ['user@gmail.com']}],
    }
    cloudflare_email_routing_rule.cloudflare_create_email_routing_rule(
        client,
        'zone-id-123',
        data,
    )
    client.post.assert_called_once_with(
        '/zones/zone-id-123/email/routing/rules',
        data=data,
    )


def test_update_rule_payload() -> None:
    """cloudflare_update_email_routing_rule sends correct payload."""
    client = mock_cloudflare_client()
    client.put.return_value = {'result': CATCH_ALL_RULE}
    data = {
        'name': 'catch-all',
        'enabled': True,
        'matchers': [{'type': 'all'}],
        'actions': [{'type': 'drop'}],
    }
    cloudflare_email_routing_rule.cloudflare_update_email_routing_rule(
        client,
        'zone-id-123',
        'rule-id-123',
        data,
    )
    client.put.assert_called_once_with(
        '/zones/zone-id-123/email/routing/rules/rule-id-123',
        data=data,
    )


def test_delete_rule_endpoint() -> None:
    """cloudflare_delete_email_routing_rule calls correct endpoint."""
    client = mock_cloudflare_client()
    client.delete.return_value = {'result': {}}
    cloudflare_email_routing_rule.cloudflare_delete_email_routing_rule(
        client,
        'zone-id-123',
        'rule-id-123',
    )
    client.delete.assert_called_once_with(
        '/zones/zone-id-123/email/routing/rules/rule-id-123',
    )
