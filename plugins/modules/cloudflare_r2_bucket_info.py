#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare R2 bucket information is gathered.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_r2_bucket_info
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare R2 bucket information is gathered
description:
  - Gathers information about Cloudflare R2 buckets.
  - Returns information about all buckets or a specific bucket.
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.account
  - damex.cloudflare.common.info_attributes
options:
  name:
    description:
      - Bucket name to query.
      - If not specified, all buckets are returned.
    type: str
"""

EXAMPLES = r"""
- name: Ensure R2 bucket information is gathered
  damex.cloudflare.cloudflare_r2_bucket_info:
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
  register: cloudflare_r2_bucket_information

- name: Ensure specific R2 bucket information is gathered
  damex.cloudflare.cloudflare_r2_bucket_info:
    name: my-bucket
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
  register: cloudflare_r2_bucket_information
"""

RETURN = r"""
buckets:
  description: R2 bucket information.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: Bucket name.
      returned: always
      type: str
    creation_date:
      description: Bucket creation timestamp.
      returned: always
      type: str
    location:
      description: Bucket location.
      returned: always
      type: str
    storage_class:
      description: Default storage class.
      returned: always
      type: str
"""

from typing import Any

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
    CloudflareNotFoundException,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_info_module,
    cloudflare_resolve_account_id,
    cloudflare_run_info_module,
)


def cloudflare_list_r2_buckets(
    client: CloudflareClient,
    account_id: str,
) -> list[dict[str, Any]]:
    """
    List all R2 buckets.

    >>> cloudflare_list_r2_buckets(client, 'acct-id')
    [{'name': 'my-bucket', 'location': 'wnam'}]
    """
    response = client.get(
        f'/accounts/{account_id}/r2/buckets',
    )
    buckets: list[dict[str, Any]] = response.get('result', {}).get('buckets', [])
    return buckets


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    argument_spec: dict[str, Any] = {
        'name': {'type': 'str'},
        'account_id': {'type': 'str'},
        'account_name': {'type': 'str'},
    }
    module = cloudflare_create_info_module(
        argument_spec,
        required_one_of=[['account_id', 'account_name']],
    )

    def _gather_r2_bucket_info() -> None:
        with cloudflare_create_client(module) as client:
            account_id = cloudflare_resolve_account_id(
                client,
                module.params.get('account_id'),
                module.params.get('account_name'),
            )
            name = module.params.get('name')

            if name:
                try:
                    response = client.get(
                        f'/accounts/{account_id}/r2/buckets/{name}',
                    )
                    bucket = response.get('result', {})
                    module.exit_json(buckets=[bucket] if bucket else [])
                except CloudflareNotFoundException:
                    module.exit_json(buckets=[])
            else:
                buckets = cloudflare_list_r2_buckets(
                    client,
                    account_id,
                )
                module.exit_json(buckets=buckets)

    cloudflare_run_info_module(module, _gather_r2_bucket_info)


if __name__ == '__main__':
    main()
