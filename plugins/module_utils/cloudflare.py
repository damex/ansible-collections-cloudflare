# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Cloudflare module framework.
"""

from __future__ import annotations

import collections.abc
from typing import Any

from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
    CloudflareClientException,
    cloudflare_create_client,
)

__all__ = [
    'CLOUDFLARE_COMMON_ARGS',
    'CLOUDFLARE_COMMON_REQUIRED_ONE_OF',
    'CLOUDFLARE_COMMON_REQUIRED_TOGETHER',
    'cloudflare_create_client',
    'cloudflare_create_info_module',
    'cloudflare_create_write_module',
    'cloudflare_find_tunnel',
    'cloudflare_get_account',
    'cloudflare_get_tunnel_configuration',
    'cloudflare_get_tunnel_token',
    'cloudflare_get_zone',
    'cloudflare_resolve_account_id',
    'cloudflare_resolve_zone_id',
    'cloudflare_run_info_module',
    'cloudflare_run_write_module',
]

CLOUDFLARE_COMMON_ARGS: dict[str, Any] = {
    'api_token': {
        'type': 'str',
        'no_log': True,
        'fallback': (env_fallback, ['CLOUDFLARE_TOKEN']),
    },
    'account_email': {'type': 'str'},
    'account_api_key': {'type': 'str', 'no_log': True},
}

CLOUDFLARE_COMMON_REQUIRED_TOGETHER: list[list[str]] = [
    ['account_email', 'account_api_key'],
]

CLOUDFLARE_COMMON_REQUIRED_ONE_OF: list[list[str]] = [
    ['api_token', 'account_api_key'],
]


def cloudflare_get_zone(
    client: CloudflareClient,
    name: str,
) -> dict[str, Any] | None:
    """
    Look up a zone by name.

    >>> cloudflare_get_zone(client, 'example.com')
    {'id': '...', 'name': 'example.com', 'status': 'active', 'type': 'full'}
    """
    response = client.get(
        '/zones',
        params={'name': name},
    )
    zones = response.get('result', [])
    return next(iter(zones), None)


def cloudflare_resolve_zone_id(
    client: CloudflareClient,
    zone_id: str | None,
    zone_name: str | None,
) -> str:
    """
    Resolve zone identifier from zone_id or zone_name.

    >>> cloudflare_resolve_zone_id(client, 'zone-123', None)
    'zone-123'
    """
    if zone_id:
        return zone_id
    if not zone_name:
        raise CloudflareClientException(
            'either zone_id or zone_name is required'
        )
    zone = cloudflare_get_zone(client, zone_name)
    if not zone:
        raise CloudflareClientException(
            f"zone '{zone_name}' not found"
        )
    resolved_zone_id: str = zone['id']
    return resolved_zone_id


def cloudflare_get_account(
    client: CloudflareClient,
    name: str,
) -> dict[str, Any] | None:
    """
    Look up an account by name.

    >>> cloudflare_get_account(client, 'my account')
    {'id': '...', 'name': 'my account'}
    """
    response = client.get(
        '/accounts',
        params={'name': name},
    )
    accounts = response.get('result', [])
    return next(iter(accounts), None)


def cloudflare_resolve_account_id(
    client: CloudflareClient,
    account_id: str | None,
    account_name: str | None,
) -> str:
    """
    Resolve account identifier from account_id or account_name.

    >>> cloudflare_resolve_account_id(client, 'acct-123', None)
    'acct-123'
    """
    if account_id:
        return account_id
    if not account_name:
        raise CloudflareClientException(
            'either account_id or account_name is required'
        )
    account = cloudflare_get_account(client, account_name)
    if not account:
        raise CloudflareClientException(
            f"account '{account_name}' not found"
        )
    resolved_account_id: str = account['id']
    return resolved_account_id


def cloudflare_create_write_module(
    argument_spec: dict[str, Any],
    required_one_of: list[list[str]] | None = None,
    mutually_exclusive: list[list[str]] | None = None,
) -> AnsibleModule:
    """
    Create write module with common Cloudflare arguments.

    >>> cloudflare_create_write_module({'name': {'type': 'str', 'required': True}})
    <AnsibleModule ...>
    """
    full_spec = argument_spec.copy()
    for spec_key, spec_value in CLOUDFLARE_COMMON_ARGS.items():
        full_spec[spec_key] = spec_value
    combined_required_one_of = list(CLOUDFLARE_COMMON_REQUIRED_ONE_OF)
    if required_one_of:
        combined_required_one_of.extend(required_one_of)
    return AnsibleModule(
        argument_spec=full_spec,
        supports_check_mode=True,
        required_together=CLOUDFLARE_COMMON_REQUIRED_TOGETHER,
        required_one_of=combined_required_one_of,
        mutually_exclusive=mutually_exclusive or [],
    )


def cloudflare_run_write_module(
    module: AnsibleModule,
    implementation: collections.abc.Callable[[], None],
) -> None:
    """
    Execute write module with exception handling.

    >>> cloudflare_run_write_module(module, implementation)
    """
    try:
        implementation()
    except CloudflareClientException as exception:
        module.fail_json(msg=str(exception))


def cloudflare_create_info_module(
    argument_spec: dict[str, Any],
    required_one_of: list[list[str]] | None = None,
    mutually_exclusive: list[list[str]] | None = None,
) -> AnsibleModule:
    """
    Create info module with common Cloudflare arguments.

    >>> cloudflare_create_info_module({'name': {'type': 'str'}})
    <AnsibleModule ...>
    """
    full_spec = argument_spec.copy()
    for spec_key, spec_value in CLOUDFLARE_COMMON_ARGS.items():
        full_spec[spec_key] = spec_value
    combined_required_one_of = list(CLOUDFLARE_COMMON_REQUIRED_ONE_OF)
    if required_one_of:
        combined_required_one_of.extend(required_one_of)
    return AnsibleModule(
        argument_spec=full_spec,
        supports_check_mode=True,
        required_together=CLOUDFLARE_COMMON_REQUIRED_TOGETHER,
        required_one_of=combined_required_one_of,
        mutually_exclusive=mutually_exclusive or [],
    )


def cloudflare_run_info_module(
    module: AnsibleModule,
    implementation: collections.abc.Callable[[], None],
) -> None:
    """
    Execute info module with exception handling.

    >>> cloudflare_run_info_module(module, implementation)
    """
    try:
        implementation()
    except CloudflareClientException as exception:
        module.fail_json(msg=str(exception))


def cloudflare_find_tunnel(
    client: CloudflareClient,
    account_id: str,
    name: str,
) -> dict[str, Any] | None:
    """
    Find a tunnel by name.

    >>> cloudflare_find_tunnel(client, 'acct-id', 'my-tunnel')
    {'id': '...', 'name': 'my-tunnel', 'status': 'healthy'}
    """
    response = client.get(
        f'/accounts/{account_id}/cfd_tunnel',
        params={
            'name': name,
            'is_deleted': 'false',
        },
    )
    tunnels: list[dict[str, Any]] = response.get('result', [])
    return next(iter(tunnels), None)


def cloudflare_get_tunnel_token(
    client: CloudflareClient,
    account_id: str,
    tunnel_id: str,
) -> str:
    """
    Get tunnel run token.

    >>> cloudflare_get_tunnel_token(client, 'acct-id', 'tunnel-id')
    'eyJ...'
    """
    response = client.get(
        f'/accounts/{account_id}/cfd_tunnel/{tunnel_id}/token',
    )
    token: str = response.get('result', '')
    return token


def cloudflare_get_tunnel_configuration(
    client: CloudflareClient,
    account_id: str,
    tunnel_id: str,
) -> dict[str, Any]:
    """
    Get tunnel ingress configuration.

    >>> cloudflare_get_tunnel_configuration(client, 'acct-id', 'tunnel-id')
    {'ingress': [{'service': 'http_status:404'}]}
    """
    response = client.get(
        f'/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations',
    )
    result = response.get('result', {})
    configuration: dict[str, Any] = result.get('config', {})
    return configuration
