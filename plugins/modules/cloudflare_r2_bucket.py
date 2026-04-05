#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare R2 buckets.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_r2_bucket
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare R2 buckets
description:
  - 'Ensures Cloudflare R2 object storage buckets using the Cloudflare API, see the docs: U(https://developers.cloudflare.com/r2/).'
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.account
attributes:
  check_mode:
    support: full
    description: Supports check mode.
  diff_mode:
    support: full
    description: Supports diff mode.
options:
  name:
    description:
      - Bucket name.
    required: true
    type: str
  state:
    description:
      - Bucket state.
    type: str
    choices:
      - absent
      - present
    default: present
  location_hint:
    description:
      - Bucket location hint.
      - Only used when creating a new bucket.
      - Cannot be changed after bucket creation.
    type: str
    choices:
      - apac
      - eeur
      - enam
      - weur
      - wnam
      - oc
  storage_class:
    description:
      - Default storage class for newly uploaded objects.
    type: str
    choices:
      - Standard
      - InfrequentAccess
    default: Standard
"""

EXAMPLES = r"""
- name: Ensure R2 bucket
  damex.cloudflare.cloudflare_r2_bucket:
    name: my-bucket
    account_id: 023e105f4ecef8ad9ca31a8372d0c353
    api_token: "{{ cloudflare_api_token }}"

- name: Ensure R2 bucket in Western Europe
  damex.cloudflare.cloudflare_r2_bucket:
    name: my-bucket
    account_id: 023e105f4ecef8ad9ca31a8372d0c353
    api_token: "{{ cloudflare_api_token }}"
    location_hint: weur

- name: Ensure R2 bucket with infrequent access storage class
  damex.cloudflare.cloudflare_r2_bucket:
    name: my-bucket
    account_id: 023e105f4ecef8ad9ca31a8372d0c353
    api_token: "{{ cloudflare_api_token }}"
    storage_class: InfrequentAccess

- name: Ensure R2 bucket is absent
  damex.cloudflare.cloudflare_r2_bucket:
    name: my-bucket
    account_id: 023e105f4ecef8ad9ca31a8372d0c353
    api_token: "{{ cloudflare_api_token }}"
    state: absent
"""

RETURN = r"""
bucket:
  description: Bucket object from the Cloudflare API.
  returned: when state is present
  type: dict
  contains:
    name:
      description: Bucket name.
      returned: success
      type: str
      sample: my-bucket
    creation_date:
      description: Bucket creation timestamp.
      returned: success
      type: str
      sample: "2024-01-01T00:00:00.000Z"
    location:
      description: Bucket location.
      returned: success
      type: str
      sample: wnam
    storage_class:
      description: Default storage class.
      returned: success
      type: str
      sample: Standard
"""

from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
    CloudflareNotFoundException,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_write_module,
    cloudflare_resolve_account_id,
    cloudflare_run_write_module,
)


def cloudflare_get_r2_bucket(
    client: CloudflareClient,
    account_id: str,
    bucket_name: str,
) -> dict[str, Any] | None:
    """
    Look up an R2 bucket by name.

    >>> cloudflare_get_r2_bucket(client, 'acct-id', 'my-bucket')
    {'name': 'my-bucket', 'location': 'wnam', 'storage_class': 'Standard'}
    """
    try:
        response = client.get(
            f'/accounts/{account_id}/r2/buckets/{bucket_name}',
        )
        bucket: dict[str, Any] = response.get('result', {})
        return bucket
    except CloudflareNotFoundException:
        return None


def cloudflare_create_r2_bucket(
    client: CloudflareClient,
    account_id: str,
    bucket_name: str,
    location_hint: str | None,
    storage_class: str,
) -> dict[str, Any]:
    """
    Create an R2 bucket.

    >>> cloudflare_create_r2_bucket(client, 'acct-id', 'my-bucket', 'wnam', 'Standard')
    {'name': 'my-bucket', 'location': 'wnam', 'storage_class': 'Standard'}
    """
    data: dict[str, Any] = {
        'name': bucket_name,
        'storageClass': storage_class,
    }
    if location_hint is not None:
        data['locationHint'] = location_hint
    response = client.post(
        f'/accounts/{account_id}/r2/buckets',
        data=data,
    )
    bucket: dict[str, Any] = response.get('result', {})
    return bucket


def cloudflare_update_r2_bucket(
    client: CloudflareClient,
    account_id: str,
    bucket_name: str,
    storage_class: str,
) -> dict[str, Any]:
    """
    Update an R2 bucket storage class.

    >>> cloudflare_update_r2_bucket(client, 'acct-id', 'my-bucket', 'InfrequentAccess')
    {'name': 'my-bucket', 'storage_class': 'InfrequentAccess'}
    """
    response = client.patch(
        f'/accounts/{account_id}/r2/buckets/{bucket_name}',
        data={'storageClass': storage_class},
    )
    bucket: dict[str, Any] = response.get('result', {})
    return bucket


def cloudflare_delete_r2_bucket(
    client: CloudflareClient,
    account_id: str,
    bucket_name: str,
) -> None:
    """
    Delete an R2 bucket.

    >>> cloudflare_delete_r2_bucket(client, 'acct-id', 'my-bucket')
    """
    client.delete(f'/accounts/{account_id}/r2/buckets/{bucket_name}')


def cloudflare_ensure_r2_bucket_present(
    module: AnsibleModule,
    client: CloudflareClient,
    account_id: str,
    name: str,
    storage_class: str,
) -> None:
    """
    Ensure R2 bucket is present.

    >>> cloudflare_ensure_r2_bucket_present(module, client, 'acct', 'b', 'Standard')
    """
    bucket = cloudflare_get_r2_bucket(client, account_id, name)

    if not bucket:
        if module.check_mode:
            module.exit_json(changed=True, bucket={})
            return
        bucket = cloudflare_create_r2_bucket(
            client,
            account_id,
            name,
            location_hint=module.params['location_hint'],
            storage_class=storage_class,
        )
        module.exit_json(
            changed=True,
            bucket=bucket,
            diff={'before': {}, 'after': bucket},
        )
        return

    if bucket.get('storage_class') != storage_class:
        before = dict(bucket)
        if not module.check_mode:
            bucket = cloudflare_update_r2_bucket(client, account_id, name, storage_class)
        else:
            bucket = dict(bucket)
            bucket['storage_class'] = storage_class
        module.exit_json(
            changed=True,
            bucket=bucket,
            diff={'before': before, 'after': bucket},
        )
        return

    module.exit_json(changed=False, bucket=bucket)


def cloudflare_ensure_r2_bucket_absent(
    module: AnsibleModule,
    client: CloudflareClient,
    account_id: str,
    name: str,
) -> None:
    """
    Ensure R2 bucket is absent.

    >>> cloudflare_ensure_r2_bucket_absent(module, client, 'acct', 'b')
    """
    bucket = cloudflare_get_r2_bucket(client, account_id, name)

    if not bucket:
        module.exit_json(changed=False)
        return

    if not module.check_mode:
        cloudflare_delete_r2_bucket(client, account_id, name)

    module.exit_json(
        changed=True,
        diff={'before': bucket, 'after': {}},
    )


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    argument_spec: dict[str, Any] = {
        'name': {'type': 'str', 'required': True},
        'account_id': {'type': 'str'},
        'account_name': {'type': 'str'},
        'state': {
            'type': 'str',
            'default': 'present',
            'choices': ['absent', 'present'],
        },
        'location_hint': {
            'type': 'str',
            'choices': ['apac', 'eeur', 'enam', 'weur', 'wnam', 'oc'],
        },
        'storage_class': {
            'type': 'str',
            'default': 'Standard',
            'choices': ['Standard', 'InfrequentAccess'],
        },
    }
    module = cloudflare_create_write_module(
        argument_spec,
        required_one_of=[['account_id', 'account_name']],
    )

    def _ensure_r2_bucket() -> None:
        with cloudflare_create_client(module) as client:
            account_id = cloudflare_resolve_account_id(
                client,
                module.params.get('account_id'),
                module.params.get('account_name'),
            )
            name = module.params['name']

            if module.params['state'] == 'present':
                cloudflare_ensure_r2_bucket_present(
                    module,
                    client,
                    account_id,
                    name,
                    module.params['storage_class'],
                )
            else:
                cloudflare_ensure_r2_bucket_absent(
                    module,
                    client,
                    account_id,
                    name,
                )

    cloudflare_run_write_module(module, _ensure_r2_bucket)


if __name__ == '__main__':
    main()
