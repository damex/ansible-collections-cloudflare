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
    CloudflareClientException,
    cloudflare_create_client,
)

__all__ = [
    'CLOUDFLARE_COMMON_ARGS',
    'CLOUDFLARE_COMMON_REQUIRED_ONE_OF',
    'CLOUDFLARE_COMMON_REQUIRED_TOGETHER',
    'cloudflare_create_client',
    'cloudflare_create_write_module',
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


def cloudflare_create_write_module(
    argument_spec: dict[str, Any],
) -> AnsibleModule:
    """
    Create write module with common Cloudflare arguments.

    >>> cloudflare_create_write_module({'name': {'type': 'str', 'required': True}})
    <AnsibleModule ...>
    """
    full_spec = argument_spec.copy()
    for spec_key, spec_value in CLOUDFLARE_COMMON_ARGS.items():
        full_spec[spec_key] = spec_value
    return AnsibleModule(
        argument_spec=full_spec,
        supports_check_mode=True,
        required_together=CLOUDFLARE_COMMON_REQUIRED_TOGETHER,
        required_one_of=CLOUDFLARE_COMMON_REQUIRED_ONE_OF,
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
