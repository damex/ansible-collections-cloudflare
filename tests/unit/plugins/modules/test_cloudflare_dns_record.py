# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the cloudflare_dns_record module.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_dns_record,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    AnsibleExitJson,
    AnsibleFailJson,
    ZONE,
    mock_cloudflare_client,
    set_module_args,
)

__all__ = [
    'test_missing_params',
    'test_present_record_exists_no_change',
    'test_present_record_created',
    'test_present_record_updated',
    'test_present_check_mode_create',
    'test_present_check_mode_update',
    'test_absent_record_exists',
    'test_absent_record_missing',
    'test_absent_check_mode',
    'test_present_mx_with_priority',
    'test_present_cname_proxied',
    'test_find_dns_record_found',
    'test_find_dns_record_not_found',
    'test_create_dns_record_payload',
    'test_delete_dns_record_endpoint',
    'test_build_record_name_subdomain',
    'test_build_record_name_apex',
    'test_build_record_name_fqdn',
    'test_zone_name_resolution',
]

A_RECORD: dict[str, Any] = {
    'id': 'record-id-123',
    'type': 'A',
    'name': 'www.example.com',
    'content': '192.0.2.1',
    'ttl': 1,
    'proxied': False,
}

ARGS: dict[str, Any] = {
    'zone_name': 'example.com',
    'api_token': 'test-token',
    'record': 'www',
    'type': 'A',
    'content': '192.0.2.1',
}


@pytest.mark.parametrize(
    'args',
    [
        {},
        {'record': 'www', 'type': 'A', 'api_token': 't'},
        {'zone_name': 'e.com', 'type': 'A', 'api_token': 't'},
        {'zone_name': 'e.com', 'record': 'www', 'api_token': 't'},
    ],
)
def test_missing_params(args: dict[str, Any]) -> None:
    """Module fails with incomplete parameters."""
    with set_module_args(args):
        with pytest.raises(AnsibleFailJson):
            cloudflare_dns_record.main()


def test_present_record_exists_no_change(dns_mock: MagicMock) -> None:
    """Existing record with matching content — no change."""
    with set_module_args(dict(ARGS)):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [A_RECORD]},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is False
    assert exc.value.result['dns_record']['content'] == '192.0.2.1'


def test_present_record_created(dns_mock: MagicMock) -> None:
    """Missing record — create it."""
    with set_module_args(dict(ARGS)):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': []},
        ]
        dns_mock.post.return_value = {'result': A_RECORD}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is True
    dns_mock.post.assert_called_once()


def test_present_record_updated(dns_mock: MagicMock) -> None:
    """Existing record with different TTL — update it."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'record': 'www',
        'type': 'A',
        'content': '192.0.2.1',
        'ttl': 3600,
    }):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [A_RECORD]},
        ]
        updated = dict(A_RECORD)
        updated['ttl'] = 3600
        dns_mock.put.return_value = {'result': updated}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is True
    assert exc.value.result['diff']['after']['ttl'] == 3600
    dns_mock.put.assert_called_once()


def test_present_check_mode_create(dns_mock: MagicMock) -> None:
    """Check mode for new record — changed=True, no POST."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'record': 'www',
        'type': 'A',
        'content': '192.0.2.1',
        '_ansible_check_mode': True,
    }):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': []},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is True
    dns_mock.post.assert_not_called()


def test_present_check_mode_update(dns_mock: MagicMock) -> None:
    """Check mode for changed record — changed=True, no PUT."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'record': 'www',
        'type': 'A',
        'content': '192.0.2.1',
        'ttl': 3600,
        '_ansible_check_mode': True,
    }):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [A_RECORD]},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is True
    dns_mock.put.assert_not_called()


def test_absent_record_exists(dns_mock: MagicMock) -> None:
    """Record exists — delete it."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'record': 'www',
        'type': 'A',
        'content': '192.0.2.1',
        'state': 'absent',
    }):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [A_RECORD]},
        ]
        dns_mock.delete.return_value = {'result': {}}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is True
    dns_mock.delete.assert_called_once_with(
        f'/zones/{ZONE["id"]}/dns_records/{A_RECORD["id"]}',
    )


def test_absent_record_missing(dns_mock: MagicMock) -> None:
    """Record missing — no change."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'record': 'www',
        'type': 'A',
        'content': '192.0.2.1',
        'state': 'absent',
    }):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': []},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is False


def test_absent_check_mode(dns_mock: MagicMock) -> None:
    """Check mode — changed=True, no DELETE."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'record': 'www',
        'type': 'A',
        'content': '192.0.2.1',
        'state': 'absent',
        '_ansible_check_mode': True,
    }):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [A_RECORD]},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is True
    dns_mock.delete.assert_not_called()


def test_present_mx_with_priority(dns_mock: MagicMock) -> None:
    """MX record with priority."""
    mx_record = {
        'id': 'mx-id',
        'type': 'MX',
        'name': 'example.com',
        'content': 'mail.example.com',
        'ttl': 1,
        'priority': 10,
        'proxied': False,
    }
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'record': '@',
        'type': 'MX',
        'content': 'mail.example.com',
        'priority': 10,
    }):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': []},
        ]
        dns_mock.post.return_value = {'result': mx_record}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is True
    post_data = dns_mock.post.call_args[1]['data']
    assert post_data['priority'] == 10
    assert post_data['name'] == 'example.com'


def test_present_cname_proxied(dns_mock: MagicMock) -> None:
    """CNAME record with proxy enabled."""
    cname_record = {
        'id': 'cname-id',
        'type': 'CNAME',
        'name': 'blog.example.com',
        'content': 'example.com',
        'ttl': 1,
        'proxied': True,
    }
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'record': 'blog',
        'type': 'CNAME',
        'content': 'example.com',
        'proxied': True,
    }):
        dns_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': []},
        ]
        dns_mock.post.return_value = {'result': cname_record}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is True
    post_data = dns_mock.post.call_args[1]['data']
    assert post_data['proxied'] is True


def test_find_dns_record_found() -> None:
    """cloudflare_find_dns_record returns record when found."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': [A_RECORD]}
    result = cloudflare_dns_record.cloudflare_find_dns_record(
        client,
        'zone-id-123',
        'A',
        'www.example.com',
        '192.0.2.1',
    )
    assert result is not None
    assert result['content'] == '192.0.2.1'


def test_find_dns_record_not_found() -> None:
    """cloudflare_find_dns_record returns None when not found."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': []}
    result = cloudflare_dns_record.cloudflare_find_dns_record(
        client,
        'zone-id-123',
        'A',
        'www.example.com',
        '192.0.2.1',
    )
    assert result is None


def test_create_dns_record_payload() -> None:
    """cloudflare_create_dns_record sends correct payload."""
    client = mock_cloudflare_client()
    client.post.return_value = {'result': A_RECORD}
    data = {
        'type': 'A',
        'name': 'www.example.com',
        'content': '192.0.2.1',
        'ttl': 1,
    }
    cloudflare_dns_record.cloudflare_create_dns_record(
        client,
        'zone-id-123',
        data,
    )
    client.post.assert_called_once_with(
        '/zones/zone-id-123/dns_records',
        data=data,
    )


def test_delete_dns_record_endpoint() -> None:
    """cloudflare_delete_dns_record calls correct endpoint."""
    client = mock_cloudflare_client()
    client.delete.return_value = {'result': {}}
    cloudflare_dns_record.cloudflare_delete_dns_record(
        client,
        'zone-id-123',
        'record-id-123',
    )
    client.delete.assert_called_once_with(
        '/zones/zone-id-123/dns_records/record-id-123',
    )


def test_build_record_name_subdomain() -> None:
    """Subdomain gets zone appended."""
    result = cloudflare_dns_record.cloudflare_build_record_name('www', 'example.com')
    assert result == 'www.example.com'


def test_build_record_name_apex() -> None:
    """@ resolves to zone name."""
    result = cloudflare_dns_record.cloudflare_build_record_name('@', 'example.com')
    assert result == 'example.com'


def test_build_record_name_fqdn() -> None:
    """Already qualified name passes through."""
    result = cloudflare_dns_record.cloudflare_build_record_name(
        'sub.example.com',
        'example.com',
    )
    assert result == 'sub.example.com'


def test_zone_name_resolution(dns_mock: MagicMock) -> None:
    """Zone name is resolved when zone_id is provided."""
    with set_module_args({
        'zone_id': 'zone-id-123',
        'api_token': 'test-token',
        'record': 'www',
        'type': 'A',
        'content': '192.0.2.1',
    }):
        dns_mock.get.side_effect = [
            {'result': {'name': 'example.com'}},
            {'result': [A_RECORD]},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_record.main()
    assert exc.value.result['changed'] is False
