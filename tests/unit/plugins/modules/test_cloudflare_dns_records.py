# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the cloudflare_dns_records module.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_dns_records,
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
    'test_no_changes',
    'test_create_new_record',
    'test_update_existing_record',
    'test_delete_existing_record',
    'test_mixed_operations',
    'test_check_mode',
    'test_empty_records_list',
    'test_compute_batch_create',
    'test_compute_batch_update',
    'test_compute_batch_delete',
    'test_compute_batch_no_changes',
    'test_compute_batch_mixed',
    'test_list_dns_records_pagination',
    'test_build_record_name_subdomain',
    'test_build_record_name_apex',
]

CURRENT_A_RECORD: dict[str, Any] = {
    'id': 'record-a-123',
    'type': 'A',
    'name': 'example.com',
    'content': '192.0.2.1',
    'ttl': 1,
    'proxied': False,
}

CURRENT_MX_RECORD: dict[str, Any] = {
    'id': 'record-mx-456',
    'type': 'MX',
    'name': 'example.com',
    'content': 'mail.example.com',
    'ttl': 1,
    'priority': 10,
    'proxied': False,
}

ARGS: dict[str, Any] = {
    'zone_name': 'example.com',
    'api_token': 'test-token',
    'records': [
        {
            'record': '@',
            'type': 'A',
            'content': '192.0.2.1',
        },
    ],
}


@pytest.mark.parametrize(
    'args',
    [
        {},
        {'zone_name': 'e.com', 'api_token': 't'},
        {'records': [], 'api_token': 't'},
    ],
)
def test_missing_params(args: dict[str, Any]) -> None:
    """Module fails with incomplete parameters."""
    with set_module_args(args):
        with pytest.raises(AnsibleFailJson):
            cloudflare_dns_records.main()


def test_no_changes(dns_records_mock: MagicMock) -> None:
    """All records already match — no change."""
    with set_module_args(dict(ARGS)):
        dns_records_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [CURRENT_A_RECORD], 'result_info': {'total_pages': 1}},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_records.main()
    assert exc.value.result['changed'] is False
    dns_records_mock.post.assert_not_called()


def test_create_new_record(dns_records_mock: MagicMock) -> None:
    """New record — batch creates it."""
    with set_module_args(dict(ARGS)):
        dns_records_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [], 'result_info': {'total_pages': 1}},
        ]
        dns_records_mock.post.return_value = {
            'result': {
                'posts': [CURRENT_A_RECORD],
                'puts': [],
                'deletes': [],
            },
        }
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_records.main()
    assert exc.value.result['changed'] is True
    assert len(exc.value.result['posts']) == 1
    dns_records_mock.post.assert_called_once()


def test_update_existing_record(dns_records_mock: MagicMock) -> None:
    """Existing record with different TTL — batch updates it."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'records': [
            {
                'record': '@',
                'type': 'A',
                'content': '192.0.2.1',
                'ttl': 3600,
            },
        ],
    }):
        dns_records_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [CURRENT_A_RECORD], 'result_info': {'total_pages': 1}},
        ]
        updated = dict(CURRENT_A_RECORD)
        updated['ttl'] = 3600
        dns_records_mock.post.return_value = {
            'result': {
                'posts': [],
                'puts': [updated],
                'deletes': [],
            },
        }
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_records.main()
    assert exc.value.result['changed'] is True
    assert len(exc.value.result['puts']) == 1
    batch_data = dns_records_mock.post.call_args[1]['data']
    assert len(batch_data['puts']) == 1
    assert batch_data['puts'][0]['ttl'] == 3600


def test_delete_existing_record(dns_records_mock: MagicMock) -> None:
    """Record marked absent — batch deletes it."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'records': [
            {
                'record': '@',
                'type': 'A',
                'content': '192.0.2.1',
                'state': 'absent',
            },
        ],
    }):
        dns_records_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [CURRENT_A_RECORD], 'result_info': {'total_pages': 1}},
        ]
        dns_records_mock.post.return_value = {
            'result': {
                'posts': [],
                'puts': [],
                'deletes': [CURRENT_A_RECORD],
            },
        }
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_records.main()
    assert exc.value.result['changed'] is True
    assert len(exc.value.result['deletes']) == 1
    batch_data = dns_records_mock.post.call_args[1]['data']
    assert batch_data['deletes'] == [{'id': 'record-a-123'}]


def test_mixed_operations(dns_records_mock: MagicMock) -> None:
    """Create, update, and delete in one batch."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'records': [
            {
                'record': '@',
                'type': 'A',
                'content': '192.0.2.1',
                'ttl': 3600,
            },
            {
                'record': 'www',
                'type': 'CNAME',
                'content': 'example.com',
            },
            {
                'record': '@',
                'type': 'MX',
                'content': 'mail.example.com',
                'state': 'absent',
            },
        ],
    }):
        dns_records_mock.get.side_effect = [
            {'result': [ZONE]},
            {
                'result': [CURRENT_A_RECORD, CURRENT_MX_RECORD],
                'result_info': {'total_pages': 1},
            },
        ]
        dns_records_mock.post.return_value = {
            'result': {
                'posts': [{'type': 'CNAME', 'name': 'www.example.com'}],
                'puts': [{'type': 'A', 'name': 'example.com', 'ttl': 3600}],
                'deletes': [CURRENT_MX_RECORD],
            },
        }
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_records.main()
    assert exc.value.result['changed'] is True
    batch_data = dns_records_mock.post.call_args[1]['data']
    assert len(batch_data['posts']) == 1
    assert len(batch_data['puts']) == 1
    assert len(batch_data['deletes']) == 1


def test_check_mode(dns_records_mock: MagicMock) -> None:
    """Check mode — changed=True, no batch POST."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'records': [
            {
                'record': 'new',
                'type': 'A',
                'content': '192.0.2.2',
            },
        ],
        '_ansible_check_mode': True,
    }):
        dns_records_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [], 'result_info': {'total_pages': 1}},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_records.main()
    assert exc.value.result['changed'] is True
    assert len(exc.value.result['posts']) == 1
    dns_records_mock.post.assert_not_called()


def test_empty_records_list(dns_records_mock: MagicMock) -> None:
    """Empty records list — no change."""
    with set_module_args({
        'zone_name': 'example.com',
        'api_token': 'test-token',
        'records': [],
    }):
        dns_records_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': [CURRENT_A_RECORD], 'result_info': {'total_pages': 1}},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_dns_records.main()
    assert exc.value.result['changed'] is False


def test_compute_batch_create() -> None:
    """cloudflare_compute_dns_batch produces posts for new records."""
    desired = [{'record': 'www', 'type': 'A', 'content': '192.0.2.1'}]
    batch = cloudflare_dns_records.cloudflare_compute_dns_batch(
        desired,
        [],
        'example.com',
    )
    assert len(batch['posts']) == 1
    assert batch['posts'][0]['name'] == 'www.example.com'
    assert not batch['puts']
    assert not batch['deletes']


def test_compute_batch_update() -> None:
    """cloudflare_compute_dns_batch produces puts for changed records."""
    desired = [{'record': '@', 'type': 'A', 'content': '192.0.2.1', 'ttl': 3600}]
    batch = cloudflare_dns_records.cloudflare_compute_dns_batch(
        desired,
        [CURRENT_A_RECORD],
        'example.com',
    )
    assert len(batch['puts']) == 1
    assert batch['puts'][0]['id'] == 'record-a-123'
    assert batch['puts'][0]['ttl'] == 3600
    assert not batch['posts']


def test_compute_batch_delete() -> None:
    """cloudflare_compute_dns_batch produces deletes for absent records."""
    desired = [{'record': '@', 'type': 'A', 'content': '192.0.2.1', 'state': 'absent'}]
    batch = cloudflare_dns_records.cloudflare_compute_dns_batch(
        desired,
        [CURRENT_A_RECORD],
        'example.com',
    )
    assert len(batch['deletes']) == 1
    assert batch['deletes'][0]['id'] == 'record-a-123'
    assert not batch['posts']
    assert not batch['puts']


def test_compute_batch_no_changes() -> None:
    """cloudflare_compute_dns_batch produces empty batch when all match."""
    desired = [{'record': '@', 'type': 'A', 'content': '192.0.2.1'}]
    batch = cloudflare_dns_records.cloudflare_compute_dns_batch(
        desired,
        [CURRENT_A_RECORD],
        'example.com',
    )
    assert not batch['posts']
    assert not batch['puts']
    assert not batch['deletes']


def test_compute_batch_mixed() -> None:
    """cloudflare_compute_dns_batch handles create, update, and delete together."""
    desired: list[dict[str, Any]] = [
        {'record': '@', 'type': 'A', 'content': '192.0.2.1', 'ttl': 3600},
        {'record': 'www', 'type': 'CNAME', 'content': 'example.com'},
        {'record': '@', 'type': 'MX', 'content': 'mail.example.com', 'state': 'absent'},
    ]
    batch = cloudflare_dns_records.cloudflare_compute_dns_batch(
        desired,
        [CURRENT_A_RECORD, CURRENT_MX_RECORD],
        'example.com',
    )
    assert len(batch['posts']) == 1
    assert len(batch['puts']) == 1
    assert len(batch['deletes']) == 1


def test_list_dns_records_pagination() -> None:
    """cloudflare_list_dns_records handles multiple pages."""
    client = mock_cloudflare_client()
    client.get.side_effect = [
        {
            'result': [CURRENT_A_RECORD],
            'result_info': {'total_pages': 2},
        },
        {
            'result': [CURRENT_MX_RECORD],
            'result_info': {'total_pages': 2},
        },
    ]
    result = cloudflare_dns_records.cloudflare_list_dns_records(
        client,
        'zone-id-123',
    )
    assert len(result) == 2
    assert client.get.call_count == 2


def test_build_record_name_subdomain() -> None:
    """Subdomain gets zone appended."""
    result = cloudflare_dns_records.cloudflare_build_record_name(
        'www',
        'example.com',
    )
    assert result == 'www.example.com'


def test_build_record_name_apex() -> None:
    """@ resolves to zone name."""
    result = cloudflare_dns_records.cloudflare_build_record_name(
        '@',
        'example.com',
    )
    assert result == 'example.com'
