# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the cloudflare_zone module.
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from ansible.module_utils.basic import AnsibleModule

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClientException,
)
from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_zone,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    ACCOUNT,
    UNIVERSAL_SSL_DISABLED,
    UNIVERSAL_SSL_ENABLED,
    ZONE,
)

__all__ = [
    'test_missing_params',
    'test_present_zone_exists',
    'test_present_zone_created',
    'test_present_verify_payload',
    'test_present_account_not_found',
    'test_present_check_mode',
    'test_absent_zone_exists',
    'test_absent_zone_missing',
    'test_absent_check_mode',
    'test_token_auth_accepted',
    'test_legacy_auth_accepted',
    'test_api_error_response',
    'test_env_token_fallback',
    'test_empty_api_token',
    'test_present_universal_ssl_changed',
    'test_present_universal_ssl_no_change',
    'test_present_ssl_mode_changed',
    'test_present_ssl_mode_no_change',
    'test_present_always_https_changed',
    'test_present_always_https_false_changed',
    'test_present_always_https_no_change',
    'test_present_min_tls_version_changed',
    'test_present_min_tls_version_no_change',
    'test_present_settings_check_mode',
]


class AnsibleExitJson(Exception):
    """
    Raised by mocked exit_json.

    >>> raise AnsibleExitJson({'changed': False})
    Traceback (most recent call last):
        ...
    test_cloudflare_zone.AnsibleExitJson: {'changed': False}
    """

    def __init__(self, result: dict[str, Any]) -> None:
        """
        Store result for assertion.

        >>> AnsibleExitJson({'changed': False}).result
        {'changed': False}
        """
        super().__init__(result)
        self.result = result


class AnsibleFailJson(Exception):
    """
    Raised by mocked fail_json.

    >>> raise AnsibleFailJson({'msg': 'error'})
    Traceback (most recent call last):
        ...
    test_cloudflare_zone.AnsibleFailJson: {'msg': 'error'}
    """

    def __init__(self, result: dict[str, Any]) -> None:
        """
        Store result for assertion.

        >>> AnsibleFailJson({'msg': 'error'}).result
        {'msg': 'error'}
        """
        super().__init__(result)
        self.result = result


def _raise_exit_json(
    module_instance: AnsibleModule,
    changed: bool = False,
    zone: dict[str, Any] | None = None,
) -> None:
    """
    Raise AnsibleExitJson with the result fields.

    >>> _raise_exit_json(module_instance, changed=False, zone={'name': 'example.com'})
    Traceback (most recent call last):
        ...
    test_cloudflare_zone.AnsibleExitJson: ...
    """
    raise AnsibleExitJson({'changed': changed, 'zone': zone})


def _raise_fail_json(
    module_instance: AnsibleModule,
    msg: str = '',
) -> None:
    """
    Raise AnsibleFailJson with the error message.

    >>> _raise_fail_json(module_instance, msg='not found')
    Traceback (most recent call last):
        ...
    test_cloudflare_zone.AnsibleFailJson: {'msg': 'not found'}
    """
    raise AnsibleFailJson({'msg': msg})


@contextmanager
def set_module_args(args: dict[str, Any]) -> Generator[None, None, None]:
    """
    Set module arguments and patch AnsibleModule for testing.

    >>> with set_module_args({'name': 'example.com', 'api_token': 't'}):
    ...     pass
    """
    args.setdefault('_ansible_remote_tmp', '/tmp')
    args.setdefault('_ansible_keep_remote_files', False)
    serialized = json.dumps({'ANSIBLE_MODULE_ARGS': args}).encode()
    with (
        patch(
            'ansible.module_utils.basic._ANSIBLE_ARGS',
            serialized,
        ),
        patch(
            'ansible.module_utils.basic._ANSIBLE_PROFILE',
            'legacy',
        ),
        patch.multiple(
            AnsibleModule,
            exit_json=_raise_exit_json,
            fail_json=_raise_fail_json,
        ),
    ):
        yield


ARGS: dict[str, str] = {
    'name': 'example.com',
    'account_name': 'my-account',
    'api_token': 'test-token',
}


@pytest.mark.parametrize(
    'args',
    [
        {},
        {'name': 'example.com', 'account_name': 'my-account'},
        {'account_name': 'my-account', 'api_token': 't'},
        {'name': 'example.com', 'api_token': 't'},
        {'name': 'example.com', 'account_name': 'a', 'account_email': 'u@e.com'},
    ],
)
def test_missing_params(args: dict[str, Any]) -> None:
    """Module fails with incomplete parameters."""
    with set_module_args(args):
        with pytest.raises(AnsibleFailJson):
            cloudflare_zone.main()


def test_present_zone_exists(cloudflare_mock: MagicMock) -> None:
    """Existing zone — no change."""
    with set_module_args(dict(ARGS)):
        cloudflare_mock.get.return_value = {'result': [ZONE]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is False
    assert exc.value.result['zone']['name'] == 'example.com'


def test_present_zone_created(cloudflare_mock: MagicMock) -> None:
    """Missing zone — create it."""
    with set_module_args(dict(ARGS)):
        cloudflare_mock.get.side_effect = [
            {'result': []},
            {'result': [ACCOUNT]},
        ]
        cloudflare_mock.post.return_value = {'result': ZONE}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.post.assert_called_once()


def test_present_verify_payload(cloudflare_mock: MagicMock) -> None:
    """Verify POST payload for zone creation."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'jump_start': True,
        'type': 'partial',
    }):
        cloudflare_mock.get.side_effect = [
            {'result': []},
            {'result': [ACCOUNT]},
        ]
        cloudflare_mock.post.return_value = {'result': ZONE}
        with pytest.raises(AnsibleExitJson):
            cloudflare_zone.main()
    cloudflare_mock.post.assert_called_once_with(
        '/zones',
        data={
            'name': 'example.com',
            'account': {'id': 'acct-id-456'},
            'jump_start': True,
            'type': 'partial',
        },
    )


def test_present_account_not_found(cloudflare_mock: MagicMock) -> None:
    """Missing account — fail."""
    with set_module_args(dict(ARGS)):
        cloudflare_mock.get.side_effect = [
            {'result': []},
            {'result': []},
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            cloudflare_zone.main()
    assert 'not found' in exc.value.result['msg']


def test_present_check_mode(cloudflare_mock: MagicMock) -> None:
    """Check mode — changed=True, no create call."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        '_ansible_check_mode': True,
    }):
        cloudflare_mock.get.return_value = {'result': []}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.post.assert_not_called()


def test_absent_zone_exists(cloudflare_mock: MagicMock) -> None:
    """Zone exists — delete it."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'state': 'absent',
    }):
        cloudflare_mock.get.return_value = {'result': [ZONE]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.delete.assert_called_once_with(f'/zones/{ZONE["id"]}')


def test_absent_zone_missing(cloudflare_mock: MagicMock) -> None:
    """Zone missing — no change."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'state': 'absent',
    }):
        cloudflare_mock.get.return_value = {'result': []}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is False
    cloudflare_mock.delete.assert_not_called()


def test_absent_check_mode(cloudflare_mock: MagicMock) -> None:
    """Check mode — changed=True, no delete call."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'state': 'absent',
        '_ansible_check_mode': True,
    }):
        cloudflare_mock.get.return_value = {'result': [ZONE]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.delete.assert_not_called()


def test_token_auth_accepted(cloudflare_mock: MagicMock) -> None:
    """Module accepts token auth and completes successfully."""
    with set_module_args(dict(ARGS)):
        cloudflare_mock.get.return_value = {'result': [ZONE]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is False


def test_legacy_auth_accepted(cloudflare_mock: MagicMock) -> None:
    """Module accepts legacy email and key auth."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'account_email': 'u@e.com',
        'account_api_key': 'legacy-key',
    }):
        cloudflare_mock.get.return_value = {'result': [ZONE]}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is False


def test_api_error_response(cloudflare_mock: MagicMock) -> None:
    """Client exception — fail_json with code and message."""
    with set_module_args(dict(ARGS)):
        cloudflare_mock.get.side_effect = CloudflareClientException(
            'API error 1003: Invalid token'
        )
        with pytest.raises(AnsibleFailJson) as exc:
            cloudflare_zone.main()
    assert '1003' in exc.value.result['msg']
    assert 'Invalid token' in exc.value.result['msg']


def test_env_token_fallback(cloudflare_mock: MagicMock) -> None:
    """CLOUDFLARE_TOKEN environment variable is used when api_token is absent."""
    with set_module_args({'name': 'example.com', 'account_name': 'my-account'}):
        with patch.dict(os.environ, {'CLOUDFLARE_TOKEN': 'env-token'}):
            cloudflare_mock.get.return_value = {'result': [ZONE]}
            with pytest.raises(AnsibleExitJson) as exc:
                cloudflare_zone.main()
    assert exc.value.result['changed'] is False


def test_empty_api_token() -> None:
    """Empty string api_token is treated as missing and fails auth."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': '',
    }):
        with pytest.raises(AnsibleFailJson) as exc:
            cloudflare_zone.main()
    assert 'api_token' in exc.value.result['msg'] or 'account_email' in exc.value.result['msg']


def test_present_universal_ssl_changed(cloudflare_mock: MagicMock) -> None:
    """universal_ssl differs from current state — changed=True and PATCH is sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'universal_ssl': True,
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': UNIVERSAL_SSL_DISABLED},
        ]
        cloudflare_mock.patch.return_value = {'result': UNIVERSAL_SSL_ENABLED}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.patch.assert_called_once_with(
        f'/zones/{ZONE["id"]}/ssl/universal/settings',
        data={'enabled': True},
    )


def test_present_universal_ssl_no_change(cloudflare_mock: MagicMock) -> None:
    """universal_ssl matches current state — changed=False, no PATCH sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'universal_ssl': True,
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': UNIVERSAL_SSL_ENABLED},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is False
    cloudflare_mock.patch.assert_not_called()


def test_present_ssl_mode_changed(cloudflare_mock: MagicMock) -> None:
    """ssl_mode differs from current state — changed=True and PATCH is sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'ssl_mode': 'full',
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': {'id': 'ssl', 'value': 'flexible'}},
        ]
        cloudflare_mock.patch.return_value = {'result': {'id': 'ssl', 'value': 'full'}}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.patch.assert_called_once_with(
        f'/zones/{ZONE["id"]}/settings/ssl',
        data={'value': 'full'},
    )


def test_present_ssl_mode_no_change(cloudflare_mock: MagicMock) -> None:
    """ssl_mode matches current state — changed=False, no PATCH sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'ssl_mode': 'full',
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': {'id': 'ssl', 'value': 'full'}},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is False
    cloudflare_mock.patch.assert_not_called()


def test_present_always_https_changed(cloudflare_mock: MagicMock) -> None:
    """always_https=True when current is off — changed=True and PATCH is sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'always_https': True,
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': {'id': 'always_use_https', 'value': 'off'}},
        ]
        cloudflare_mock.patch.return_value = {'result': {'id': 'always_use_https', 'value': 'on'}}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.patch.assert_called_once_with(
        f'/zones/{ZONE["id"]}/settings/always_use_https',
        data={'value': 'on'},
    )


def test_present_always_https_false_changed(cloudflare_mock: MagicMock) -> None:
    """always_https=False when current is on — changed=True and PATCH sends off."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'always_https': False,
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': {'id': 'always_use_https', 'value': 'on'}},
        ]
        cloudflare_mock.patch.return_value = {'result': {'id': 'always_use_https', 'value': 'off'}}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.patch.assert_called_once_with(
        f'/zones/{ZONE["id"]}/settings/always_use_https',
        data={'value': 'off'},
    )


def test_present_always_https_no_change(cloudflare_mock: MagicMock) -> None:
    """always_https=True when current is on — changed=False, no PATCH sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'always_https': True,
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': {'id': 'always_use_https', 'value': 'on'}},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is False
    cloudflare_mock.patch.assert_not_called()


def test_present_min_tls_version_changed(cloudflare_mock: MagicMock) -> None:
    """min_tls_version differs from current state — changed=True and PATCH is sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'min_tls_version': '1.2',
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': {'id': 'min_tls_version', 'value': '1.0'}},
        ]
        cloudflare_mock.patch.return_value = {'result': {'id': 'min_tls_version', 'value': '1.2'}}
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.patch.assert_called_once_with(
        f'/zones/{ZONE["id"]}/settings/min_tls_version',
        data={'value': '1.2'},
    )


def test_present_min_tls_version_no_change(cloudflare_mock: MagicMock) -> None:
    """min_tls_version matches current state — changed=False, no PATCH sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'min_tls_version': '1.2',
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': {'id': 'min_tls_version', 'value': '1.2'}},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is False
    cloudflare_mock.patch.assert_not_called()


def test_present_settings_check_mode(cloudflare_mock: MagicMock) -> None:
    """Check mode with differing setting — changed=True but no PATCH sent."""
    with set_module_args({
        'name': 'example.com',
        'account_name': 'my-account',
        'api_token': 'test-token',
        'universal_ssl': True,
        '_ansible_check_mode': True,
    }):
        cloudflare_mock.get.side_effect = [
            {'result': [ZONE]},
            {'result': UNIVERSAL_SSL_DISABLED},
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result['changed'] is True
    cloudflare_mock.patch.assert_not_called()
