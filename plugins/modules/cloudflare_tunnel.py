#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare tunnels.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_tunnel
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare tunnel
description:
  - 'Ensures Cloudflare tunnels with ingress configuration, see the docs: U(https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/).'
  - Creates the tunnel if missing, updates ingress if changed, deletes if absent.
  - Returns the tunnel token for use with cloudflared.
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.account
attributes:
  diff_mode:
    support: full
    description: Supports diff mode.
  check_mode:
    support: full
    description: Supports check mode.
options:
  name:
    description:
      - Tunnel name.
    required: true
    type: str
  state:
    description:
      - Tunnel state.
    type: str
    choices:
      - absent
      - present
    default: present
  ingress:
    description:
      - Ingress rules for the tunnel.
      - Must end with a catch-all rule without hostname.
      - Required when O(state) is C(present).
    type: list
    elements: dict
    suboptions:
      hostname:
        description:
          - Hostname to match.
          - Omit for the catch-all rule.
        type: str
      service:
        description:
          - Service URL or status code.
        required: true
        type: str
      origin_request:
        description:
          - Origin request parameters.
        type: dict
"""

EXAMPLES = r"""
- name: Ensure tunnel with ingress
  damex.cloudflare.cloudflare_tunnel:
    name: hetzner
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
    ingress:
      - hostname: forgejo.damex.org
        service: http://localhost:3000
      - hostname: nextcloud.damex.org
        service: http://localhost:8080
      - service: http_status:404

- name: Ensure tunnel is absent
  damex.cloudflare.cloudflare_tunnel:
    name: old-tunnel
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
    state: absent
"""

RETURN = r"""
tunnel:
  description: Tunnel object from the Cloudflare API.
  returned: when state is present
  type: dict
  contains:
    id:
      description: Tunnel identifier.
      returned: success
      type: str
    name:
      description: Tunnel name.
      returned: success
      type: str
    status:
      description: Tunnel status.
      returned: success
      type: str
    token:
      description: Tunnel run token for cloudflared.
      returned: success
      type: str
"""

from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
    CloudflareClientException,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_write_module,
    cloudflare_resolve_account_id,
    cloudflare_run_write_module,
)


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


def cloudflare_create_tunnel(
    client: CloudflareClient,
    account_id: str,
    name: str,
) -> dict[str, Any]:
    """
    Create a tunnel.

    >>> cloudflare_create_tunnel(client, 'acct-id', 'my-tunnel')
    {'id': '...', 'name': 'my-tunnel', 'token': '...'}
    """
    response = client.post(
        f'/accounts/{account_id}/cfd_tunnel',
        data={
            'name': name,
            'config_src': 'cloudflare',
        },
    )
    tunnel: dict[str, Any] = response.get('result', {})
    return tunnel


def cloudflare_delete_tunnel(
    client: CloudflareClient,
    account_id: str,
    tunnel_id: str,
) -> None:
    """
    Delete a tunnel.

    >>> cloudflare_delete_tunnel(client, 'acct-id', 'tunnel-id')
    """
    client.delete(f'/accounts/{account_id}/cfd_tunnel/{tunnel_id}')


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
    {'ingress': [{'hostname': 'app.example.com', 'service': 'http://localhost:8080'}]}
    """
    response = client.get(
        f'/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations',
    )
    result = response.get('result', {})
    configuration: dict[str, Any] = result.get('config', {})
    return configuration


def cloudflare_set_tunnel_configuration(
    client: CloudflareClient,
    account_id: str,
    tunnel_id: str,
    ingress: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Set tunnel ingress configuration.

    >>> cloudflare_set_tunnel_configuration(client, 'acct-id', 'tunnel-id', [{'service': 'http_status:404'}])
    {'ingress': [{'service': 'http_status:404'}]}
    """
    response = client.put(
        f'/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations',
        data={
            'config': {
                'ingress': ingress,
            },
        },
    )
    result = response.get('result', {})
    configuration: dict[str, Any] = result.get('config', {})
    return configuration


def _build_ingress(
    module_ingress: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build ingress payload from module parameters.

    >>> _build_ingress([{'hostname': 'app.example.com', 'service': 'http://localhost:8080'}])
    [{'hostname': 'app.example.com', 'service': 'http://localhost:8080'}]
    """
    ingress: list[dict[str, Any]] = []
    for rule in module_ingress:
        entry: dict[str, Any] = {
            'service': rule['service'],
        }
        hostname = rule.get('hostname')
        if hostname:
            entry['hostname'] = hostname
        origin_request = rule.get('origin_request')
        if origin_request:
            entry['originRequest'] = origin_request
        ingress.append(entry)
    return ingress


def _ingress_matches(
    current_ingress: list[dict[str, Any]],
    desired_ingress: list[dict[str, Any]],
) -> bool:
    """
    Check if current ingress matches desired.

    >>> _ingress_matches([{'service': 'http_status:404'}], [{'service': 'http_status:404'}])
    True
    """
    if len(current_ingress) != len(desired_ingress):
        return False
    for current_rule, desired_rule in zip(current_ingress, desired_ingress):
        if current_rule.get('hostname') != desired_rule.get('hostname'):
            return False
        if current_rule.get('service') != desired_rule.get('service'):
            return False
        if current_rule.get('originRequest') != desired_rule.get('originRequest'):
            return False
    return True


def cloudflare_ensure_tunnel_present(
    module: AnsibleModule,
    client: CloudflareClient,
    account_id: str,
) -> None:
    """
    Ensure tunnel is present with correct ingress.

    >>> cloudflare_ensure_tunnel_present(module, client, 'acct-id')
    """
    name = module.params['name']
    ingress = module.params.get('ingress')
    if not ingress:
        raise CloudflareClientException('ingress is required when state is present')

    desired_ingress = _build_ingress(ingress)
    tunnel = cloudflare_find_tunnel(client, account_id, name)

    if not tunnel:
        if module.check_mode:
            module.exit_json(changed=True, tunnel={})
            return
        tunnel = cloudflare_create_tunnel(client, account_id, name)
        cloudflare_set_tunnel_configuration(
            client,
            account_id,
            tunnel['id'],
            desired_ingress,
        )
        token = cloudflare_get_tunnel_token(client, account_id, tunnel['id'])
        tunnel['token'] = token
        module.exit_json(
            changed=True,
            tunnel=tunnel,
            diff={
                'before': {},
                'after': {'ingress': desired_ingress},
            },
        )
        return

    current_configuration = cloudflare_get_tunnel_configuration(
        client,
        account_id,
        tunnel['id'],
    )
    current_ingress = current_configuration.get('ingress', [])

    if _ingress_matches(current_ingress, desired_ingress):
        token = cloudflare_get_tunnel_token(client, account_id, tunnel['id'])
        tunnel['token'] = token
        module.exit_json(changed=False, tunnel=tunnel)
        return

    if module.check_mode:
        tunnel['token'] = ''
        module.exit_json(
            changed=True,
            tunnel=tunnel,
            diff={
                'before': {'ingress': current_ingress},
                'after': {'ingress': desired_ingress},
            },
        )
        return

    cloudflare_set_tunnel_configuration(
        client,
        account_id,
        tunnel['id'],
        desired_ingress,
    )
    token = cloudflare_get_tunnel_token(client, account_id, tunnel['id'])
    tunnel['token'] = token
    module.exit_json(
        changed=True,
        tunnel=tunnel,
        diff={
            'before': {'ingress': current_ingress},
            'after': {'ingress': desired_ingress},
        },
    )


def cloudflare_ensure_tunnel_absent(
    module: AnsibleModule,
    client: CloudflareClient,
    account_id: str,
) -> None:
    """
    Ensure tunnel is absent.

    >>> cloudflare_ensure_tunnel_absent(module, client, 'acct-id')
    """
    name = module.params['name']
    tunnel = cloudflare_find_tunnel(client, account_id, name)

    if not tunnel:
        module.exit_json(changed=False)
        return

    if not module.check_mode:
        cloudflare_delete_tunnel(client, account_id, tunnel['id'])

    module.exit_json(
        changed=True,
        diff={
            'before': tunnel,
            'after': {},
        },
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
        'ingress': {
            'type': 'list',
            'elements': 'dict',
            'options': {
                'hostname': {'type': 'str'},
                'service': {'type': 'str', 'required': True},
                'origin_request': {'type': 'dict'},
            },
        },
    }
    module = cloudflare_create_write_module(
        argument_spec,
        required_one_of=[['account_id', 'account_name']],
    )

    def _ensure_tunnel() -> None:
        with cloudflare_create_client(module) as client:
            account_id = cloudflare_resolve_account_id(
                client,
                module.params.get('account_id'),
                module.params.get('account_name'),
            )

            if module.params['state'] == 'present':
                cloudflare_ensure_tunnel_present(
                    module,
                    client,
                    account_id,
                )
            else:
                cloudflare_ensure_tunnel_absent(
                    module,
                    client,
                    account_id,
                )

    cloudflare_run_write_module(module, _ensure_tunnel)


if __name__ == '__main__':
    main()
