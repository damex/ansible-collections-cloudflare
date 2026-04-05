#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare email routing destination addresses.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_email_routing_address
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare email routing destination address
description:
  - 'Ensures Cloudflare email routing destination addresses, see the docs: U(https://developers.cloudflare.com/email-routing/).'
  - Destination addresses must be verified before they can be used in routing rules.
  - Creating an address triggers a verification email.
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.account
  - damex.cloudflare.common.write_attributes
options:
  email:
    description:
      - Destination email address.
    required: true
    type: str
  state:
    description:
      - Destination address state.
    type: str
    choices:
      - absent
      - present
    default: present
"""

EXAMPLES = r"""
- name: Ensure destination address
  damex.cloudflare.cloudflare_email_routing_address:
    email: user@gmail.com
    account_id: 023e105f4ecef8ad9ca31a8372d0c353
    api_token: "{{ cloudflare_api_token }}"

- name: Ensure destination address is absent
  damex.cloudflare.cloudflare_email_routing_address:
    email: old@gmail.com
    account_id: 023e105f4ecef8ad9ca31a8372d0c353
    api_token: "{{ cloudflare_api_token }}"
    state: absent
"""

RETURN = r"""
address:
  description: Destination address object from the Cloudflare API.
  returned: when state is present
  type: dict
  contains:
    id:
      description: Address identifier.
      returned: success
      type: str
    email:
      description: Destination email address.
      returned: success
      type: str
    verified:
      description: Verification timestamp, null if not yet verified.
      returned: success
      type: str
"""

from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_write_module,
    cloudflare_resolve_account_id,
    cloudflare_run_write_module,
)


def cloudflare_find_email_routing_address(
    client: CloudflareClient,
    account_id: str,
    email: str,
) -> dict[str, Any] | None:
    """
    Find a destination address by email.

    >>> cloudflare_find_email_routing_address(client, 'acct-id', 'u@example.com')
    {'id': '...', 'email': 'u@example.com', 'verified': '2024-01-01T00:00:00Z'}
    """
    response = client.get(
        f'/accounts/{account_id}/email/routing/addresses',
    )
    addresses: list[dict[str, Any]] = response.get('result', [])
    for address in addresses:
        if address.get('email') == email:
            return address
    return None


def cloudflare_create_email_routing_address(
    client: CloudflareClient,
    account_id: str,
    email: str,
) -> dict[str, Any]:
    """
    Create a destination address.

    >>> cloudflare_create_email_routing_address(client, 'acct-id', 'u@example.com')
    {'id': '...', 'email': 'u@example.com', 'verified': None}
    """
    response = client.post(
        f'/accounts/{account_id}/email/routing/addresses',
        data={'email': email},
    )
    address: dict[str, Any] = response.get('result', {})
    return address


def cloudflare_delete_email_routing_address(
    client: CloudflareClient,
    account_id: str,
    address_id: str,
) -> None:
    """
    Delete a destination address.

    >>> cloudflare_delete_email_routing_address(client, 'acct-id', 'addr-id')
    """
    client.delete(
        f'/accounts/{account_id}/email/routing/addresses/{address_id}',
    )


def cloudflare_ensure_email_routing_address_present(
    module: AnsibleModule,
    client: CloudflareClient,
    account_id: str,
    email: str,
) -> None:
    """
    Ensure destination address is present.

    >>> cloudflare_ensure_email_routing_address_present(module, client, 'acct', 'u@e.com')
    """
    address = cloudflare_find_email_routing_address(
        client,
        account_id,
        email,
    )

    if address:
        module.exit_json(
            changed=False,
            address=address,
        )
        return

    if module.check_mode:
        module.exit_json(
            changed=True,
            address={},
        )
        return

    address = cloudflare_create_email_routing_address(
        client,
        account_id,
        email,
    )
    module.exit_json(
        changed=True,
        address=address,
        diff={
            'before': {},
            'after': address,
        },
    )


def cloudflare_ensure_email_routing_address_absent(
    module: AnsibleModule,
    client: CloudflareClient,
    account_id: str,
    email: str,
) -> None:
    """
    Ensure destination address is absent.

    >>> cloudflare_ensure_email_routing_address_absent(module, client, 'acct', 'u@e.com')
    """
    address = cloudflare_find_email_routing_address(
        client,
        account_id,
        email,
    )

    if not address:
        module.exit_json(changed=False)
        return

    if not module.check_mode:
        cloudflare_delete_email_routing_address(
            client,
            account_id,
            address['id'],
        )

    module.exit_json(
        changed=True,
        diff={
            'before': address,
            'after': {},
        },
    )


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    argument_spec: dict[str, Any] = {
        'email': {'type': 'str', 'required': True},
        'account_id': {'type': 'str'},
        'account_name': {'type': 'str'},
        'state': {
            'type': 'str',
            'default': 'present',
            'choices': ['absent', 'present'],
        },
    }
    module = cloudflare_create_write_module(
        argument_spec,
        required_one_of=[['account_id', 'account_name']],
    )

    def _ensure_email_routing_address() -> None:
        with cloudflare_create_client(module) as client:
            account_id = cloudflare_resolve_account_id(
                client,
                module.params.get('account_id'),
                module.params.get('account_name'),
            )
            email = module.params['email']

            if module.params['state'] == 'present':
                cloudflare_ensure_email_routing_address_present(
                    module,
                    client,
                    account_id,
                    email,
                )
            else:
                cloudflare_ensure_email_routing_address_absent(
                    module,
                    client,
                    account_id,
                    email,
                )

    cloudflare_run_write_module(module, _ensure_email_routing_address)


if __name__ == '__main__':
    main()
