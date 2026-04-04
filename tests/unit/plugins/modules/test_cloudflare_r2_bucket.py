# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the cloudflare_r2_bucket module.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareNotFoundException,
)
from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_r2_bucket,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    AnsibleExitJson,
    AnsibleFailJson,
    mock_cloudflare_client,
    set_module_args,
)

__all__ = [
    'test_missing_params',
    'test_present_bucket_exists_no_change',
    'test_present_bucket_created',
    'test_present_bucket_created_with_location',
    'test_present_verify_create_payload',
    'test_present_storage_class_changed',
    'test_present_check_mode_create',
    'test_present_check_mode_update',
    'test_absent_bucket_exists',
    'test_absent_bucket_missing',
    'test_absent_check_mode',
    'test_get_r2_bucket_found',
    'test_get_r2_bucket_not_found',
    'test_create_r2_bucket_payload',
    'test_update_r2_bucket_payload',
    'test_delete_r2_bucket_endpoint',
    'test_present_account_name_resolved',
]

BUCKET: dict[str, Any] = {
    'name': 'my-bucket',
    'creation_date': '2024-01-01T00:00:00.000Z',
    'location': 'wnam',
    'storage_class': 'Standard',
}

ARGS: dict[str, str] = {
    'name': 'my-bucket',
    'account_id': 'acct-id-456',
    'api_token': 'test-token',
}


@pytest.mark.parametrize(
    'args',
    [
        {},
        {'name': 'my-bucket', 'api_token': 't'},
        {'account_id': 'a', 'api_token': 't'},
        {'name': 'my-bucket', 'account_id': 'a'},
    ],
)
def test_missing_params(args: dict[str, Any]) -> None:
    """Module fails with incomplete parameters."""
    with set_module_args(args):
        with pytest.raises(AnsibleFailJson):
            cloudflare_r2_bucket.main()


def test_present_bucket_exists_no_change(r2_mock: MagicMock) -> None:
    """Existing bucket with matching storage class — no change."""
    with set_module_args(dict(ARGS)):
        r2_mock.get.return_value = {'result': BUCKET}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is False
    assert exc.value.result['bucket']['name'] == 'my-bucket'


def test_present_bucket_created(r2_mock: MagicMock) -> None:
    """Missing bucket — create it."""
    with set_module_args(dict(ARGS)):
        r2_mock.get.side_effect = CloudflareNotFoundException('not found')
        r2_mock.post.return_value = {'result': BUCKET}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is True
    assert exc.value.result['bucket']['name'] == 'my-bucket'
    r2_mock.post.assert_called_once()


def test_present_bucket_created_with_location(r2_mock: MagicMock) -> None:
    """Bucket created with location hint."""
    with set_module_args({
        'name': 'my-bucket',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'location_hint': 'weur',
    }):
        r2_mock.get.side_effect = CloudflareNotFoundException('not found')
        r2_mock.post.return_value = {'result': BUCKET}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is True
    r2_mock.post.assert_called_once_with(
        '/accounts/acct-id-456/r2/buckets',
        data={
            'name': 'my-bucket',
            'storageClass': 'Standard',
            'locationHint': 'weur',
        },
    )


def test_present_verify_create_payload(r2_mock: MagicMock) -> None:
    """Verify POST payload without location hint."""
    with set_module_args(dict(ARGS)):
        r2_mock.get.side_effect = CloudflareNotFoundException('not found')
        r2_mock.post.return_value = {'result': BUCKET}
        with pytest.raises(AnsibleExitJson):
            cloudflare_r2_bucket.main()
    r2_mock.post.assert_called_once_with(
        '/accounts/acct-id-456/r2/buckets',
        data={
            'name': 'my-bucket',
            'storageClass': 'Standard',
        },
    )


def test_present_storage_class_changed(r2_mock: MagicMock) -> None:
    """Storage class differs — changed=True and PATCH is sent."""
    with set_module_args({
        'name': 'my-bucket',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'storage_class': 'InfrequentAccess',
    }):
        r2_mock.get.return_value = {'result': BUCKET}
        updated_bucket = dict(BUCKET)
        updated_bucket['storage_class'] = 'InfrequentAccess'
        r2_mock.patch.return_value = {'result': updated_bucket}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is True
    assert exc.value.result['diff']['before']['storage_class'] == 'Standard'
    assert exc.value.result['diff']['after']['storage_class'] == 'InfrequentAccess'
    r2_mock.patch.assert_called_once_with(
        '/accounts/acct-id-456/r2/buckets/my-bucket',
        data={'storageClass': 'InfrequentAccess'},
    )


def test_present_check_mode_create(r2_mock: MagicMock) -> None:
    """Check mode for new bucket — changed=True, no POST."""
    with set_module_args({
        'name': 'my-bucket',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        '_ansible_check_mode': True,
    }):
        r2_mock.get.side_effect = CloudflareNotFoundException('not found')
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is True
    r2_mock.post.assert_not_called()


def test_present_check_mode_update(r2_mock: MagicMock) -> None:
    """Check mode for storage class change — changed=True, no PATCH."""
    with set_module_args({
        'name': 'my-bucket',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'storage_class': 'InfrequentAccess',
        '_ansible_check_mode': True,
    }):
        r2_mock.get.return_value = {'result': BUCKET}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is True
    assert exc.value.result['diff']['after']['storage_class'] == 'InfrequentAccess'
    r2_mock.patch.assert_not_called()


def test_absent_bucket_exists(r2_mock: MagicMock) -> None:
    """Bucket exists — delete it."""
    with set_module_args({
        'name': 'my-bucket',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'state': 'absent',
    }):
        r2_mock.get.return_value = {'result': BUCKET}
        r2_mock.delete.return_value = {'result': {}}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is True
    r2_mock.delete.assert_called_once_with(
        '/accounts/acct-id-456/r2/buckets/my-bucket',
    )


def test_absent_bucket_missing(r2_mock: MagicMock) -> None:
    """Bucket missing — no change."""
    with set_module_args({
        'name': 'my-bucket',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'state': 'absent',
    }):
        r2_mock.get.side_effect = CloudflareNotFoundException('not found')
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is False
    r2_mock.delete.assert_not_called()


def test_absent_check_mode(r2_mock: MagicMock) -> None:
    """Check mode — changed=True, no DELETE."""
    with set_module_args({
        'name': 'my-bucket',
        'account_id': 'acct-id-456',
        'api_token': 'test-token',
        'state': 'absent',
        '_ansible_check_mode': True,
    }):
        r2_mock.get.return_value = {'result': BUCKET}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is True
    r2_mock.delete.assert_not_called()


def test_get_r2_bucket_found() -> None:
    """cloudflare_get_r2_bucket returns bucket dict when found."""
    client = mock_cloudflare_client()
    client.get.return_value = {'result': BUCKET}
    result = cloudflare_r2_bucket.cloudflare_get_r2_bucket(
        client,
        'acct-id-456',
        'my-bucket',
    )
    assert result is not None
    assert result['name'] == 'my-bucket'
    client.get.assert_called_once_with(
        '/accounts/acct-id-456/r2/buckets/my-bucket',
    )


def test_get_r2_bucket_not_found() -> None:
    """cloudflare_get_r2_bucket returns None when bucket does not exist."""
    client = mock_cloudflare_client()
    client.get.side_effect = CloudflareNotFoundException('not found')
    result = cloudflare_r2_bucket.cloudflare_get_r2_bucket(
        client,
        'acct-id-456',
        'missing',
    )
    assert result is None


def test_create_r2_bucket_payload() -> None:
    """cloudflare_create_r2_bucket sends correct POST payload."""
    client = mock_cloudflare_client()
    client.post.return_value = {'result': BUCKET}
    cloudflare_r2_bucket.cloudflare_create_r2_bucket(
        client,
        'acct-id-456',
        'my-bucket',
        location_hint='weur',
        storage_class='Standard',
    )
    client.post.assert_called_once_with(
        '/accounts/acct-id-456/r2/buckets',
        data={
            'name': 'my-bucket',
            'storageClass': 'Standard',
            'locationHint': 'weur',
        },
    )


def test_update_r2_bucket_payload() -> None:
    """cloudflare_update_r2_bucket sends correct PATCH payload."""
    client = mock_cloudflare_client()
    client.patch.return_value = {'result': BUCKET}
    cloudflare_r2_bucket.cloudflare_update_r2_bucket(
        client,
        'acct-id-456',
        'my-bucket',
        'InfrequentAccess',
    )
    client.patch.assert_called_once_with(
        '/accounts/acct-id-456/r2/buckets/my-bucket',
        data={'storageClass': 'InfrequentAccess'},
    )


def test_delete_r2_bucket_endpoint() -> None:
    """cloudflare_delete_r2_bucket calls delete with correct path."""
    client = mock_cloudflare_client()
    client.delete.return_value = {'result': {}}
    cloudflare_r2_bucket.cloudflare_delete_r2_bucket(
        client,
        'acct-id-456',
        'my-bucket',
    )
    client.delete.assert_called_once_with(
        '/accounts/acct-id-456/r2/buckets/my-bucket',
    )


def test_present_account_name_resolved(r2_mock: MagicMock) -> None:
    """Account name is resolved to account ID via API lookup."""
    with set_module_args({
        'name': 'my-bucket',
        'account_name': 'my-account',
        'api_token': 'test-token',
    }):
        r2_mock.get.side_effect = [
            {'result': [{'id': 'resolved-id', 'name': 'my-account'}]},
            {'result': BUCKET},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_r2_bucket.main()
    assert exc.value.result['changed'] is False
    assert exc.value.result['bucket']['name'] == 'my-bucket'
