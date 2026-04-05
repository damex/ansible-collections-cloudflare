# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Shared fixtures and constants for cloudflare module unit tests.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from ansible.module_utils.basic import AnsibleModule

__all__ = [
    'ZONE',
    'ACCOUNT',
    'UNIVERSAL_SSL_ENABLED',
    'UNIVERSAL_SSL_DISABLED',
    'CLOUDFLARE_ZONE_MODULE',
    'AnsibleExitJson',
    'AnsibleFailJson',
    'mock_cloudflare_client',
    'cloudflare_mock',
    'r2_mock',
    'email_routing_mock',
    'address_mock',
    'rule_mock',
    'dns_mock',
    'set_module_args',
]

CLOUDFLARE_DNS_RECORD_MODULE = (
    'ansible_collections.damex.cloudflare.plugins.modules.cloudflare_dns_record'
)

CLOUDFLARE_R2_MODULE = (
    'ansible_collections.damex.cloudflare.plugins.modules.cloudflare_r2_bucket'
)

ZONE: dict[str, Any] = {
    'id': 'zone-id-123',
    'name': 'example.com',
    'status': 'active',
    'type': 'full',
    'account': {'id': 'acct-id-456', 'name': 'my-account'},
}

ACCOUNT: dict[str, str] = {'id': 'acct-id-456', 'name': 'my-account'}

UNIVERSAL_SSL_ENABLED: dict[str, bool] = {'enabled': True}
UNIVERSAL_SSL_DISABLED: dict[str, bool] = {'enabled': False}

CLOUDFLARE_ZONE_MODULE = (
    'ansible_collections.damex.cloudflare.plugins.modules.cloudflare_zone'
)


class AnsibleExitJson(Exception):
    """
    Raised by mocked exit_json.

    >>> raise AnsibleExitJson({'changed': False})
    Traceback (most recent call last):
        ...
    conftest.AnsibleExitJson: {'changed': False}
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
    conftest.AnsibleFailJson: {'msg': 'error'}
    """

    def __init__(self, result: dict[str, Any]) -> None:
        """
        Store result for assertion.

        >>> AnsibleFailJson({'msg': 'error'}).result
        {'msg': 'error'}
        """
        super().__init__(result)
        self.result = result


@contextmanager
def set_module_args(
    args: dict[str, Any],
    exit_json_mock: Callable[..., None] | None = None,
    fail_json_mock: Callable[..., None] | None = None,
) -> Generator[None, None, None]:
    """
    Set module arguments and patch AnsibleModule for testing.

    >>> with set_module_args({'name': 'example.com', 'api_token': 't'}):
    ...     pass
    """
    args.setdefault('_ansible_remote_tmp', '/tmp')
    args.setdefault('_ansible_keep_remote_files', False)
    serialized = json.dumps({'ANSIBLE_MODULE_ARGS': args}).encode()
    exit_function = exit_json_mock or _default_raise_exit_json
    fail_function = fail_json_mock or _default_raise_fail_json
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
            exit_json=exit_function,
            fail_json=fail_function,
        ),
    ):
        yield


def _default_raise_exit_json(
    module_instance: AnsibleModule,
    **kwargs: Any,
) -> None:
    """
    Raise AnsibleExitJson with all keyword arguments.

    >>> _default_raise_exit_json(module_instance, changed=False)
    Traceback (most recent call last):
        ...
    conftest.AnsibleExitJson: {'changed': False}
    """
    raise AnsibleExitJson(kwargs)


def _default_raise_fail_json(
    module_instance: AnsibleModule,
    msg: str = '',
) -> None:
    """
    Raise AnsibleFailJson with the error message.

    >>> _default_raise_fail_json(module_instance, msg='not found')
    Traceback (most recent call last):
        ...
    conftest.AnsibleFailJson: {'msg': 'not found'}
    """
    raise AnsibleFailJson({'msg': msg})


def mock_cloudflare_client() -> MagicMock:
    """
    Create mock CloudflareClient with context manager support.

    >>> mock_cloudflare_client()
    <MagicMock ...>
    """
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


@pytest.fixture
def cloudflare_mock() -> Generator[MagicMock, None, None]:
    """
    Patch cloudflare_create_client for the test duration.

    >>> type(next(cloudflare_mock()))
    <class 'unittest.mock.MagicMock'>
    """
    client = mock_cloudflare_client()
    with patch(
        f'{CLOUDFLARE_ZONE_MODULE}.cloudflare_create_client',
        return_value=client,
    ):
        yield client


@pytest.fixture
def r2_mock() -> Generator[MagicMock, None, None]:
    """
    Patch cloudflare_create_client for R2 tests.

    >>> type(next(r2_mock()))
    <class 'unittest.mock.MagicMock'>
    """
    client = mock_cloudflare_client()
    with patch(
        f'{CLOUDFLARE_R2_MODULE}.cloudflare_create_client',
        return_value=client,
    ):
        yield client


CLOUDFLARE_EMAIL_ROUTING_MODULE = (
    'ansible_collections.damex.cloudflare.plugins.modules.cloudflare_email_routing'
)

CLOUDFLARE_EMAIL_ADDRESS_MODULE = (
    'ansible_collections.damex.cloudflare.plugins.modules.cloudflare_email_routing_address'
)

CLOUDFLARE_EMAIL_RULE_MODULE = (
    'ansible_collections.damex.cloudflare.plugins.modules.cloudflare_email_routing_rule'
)


@pytest.fixture
def email_routing_mock() -> Generator[MagicMock, None, None]:
    """
    Patch cloudflare_create_client for email routing tests.

    >>> type(next(email_routing_mock()))
    <class 'unittest.mock.MagicMock'>
    """
    client = mock_cloudflare_client()
    with patch(
        f'{CLOUDFLARE_EMAIL_ROUTING_MODULE}.cloudflare_create_client',
        return_value=client,
    ):
        yield client


@pytest.fixture
def address_mock() -> Generator[MagicMock, None, None]:
    """
    Patch cloudflare_create_client for email address tests.

    >>> type(next(address_mock()))
    <class 'unittest.mock.MagicMock'>
    """
    client = mock_cloudflare_client()
    with patch(
        f'{CLOUDFLARE_EMAIL_ADDRESS_MODULE}.cloudflare_create_client',
        return_value=client,
    ):
        yield client


@pytest.fixture
def rule_mock() -> Generator[MagicMock, None, None]:
    """
    Patch cloudflare_create_client for email rule tests.

    >>> type(next(rule_mock()))
    <class 'unittest.mock.MagicMock'>
    """
    client = mock_cloudflare_client()
    with patch(
        f'{CLOUDFLARE_EMAIL_RULE_MODULE}.cloudflare_create_client',
        return_value=client,
    ):
        yield client


@pytest.fixture
def dns_mock() -> Generator[MagicMock, None, None]:
    """
    Patch cloudflare_create_client for DNS record tests.

    >>> type(next(dns_mock()))
    <class 'unittest.mock.MagicMock'>
    """
    client = mock_cloudflare_client()
    with patch(
        f'{CLOUDFLARE_DNS_RECORD_MODULE}.cloudflare_create_client',
        return_value=client,
    ):
        yield client
