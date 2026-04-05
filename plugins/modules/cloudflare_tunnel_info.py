#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare tunnel information is gathered.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_tunnel_info
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare tunnel information is gathered
description:
  - Gathers Cloudflare tunnel information including the run token.
  - 'See the docs: U(https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/).'
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.account
  - damex.cloudflare.common.info_attributes
options:
  name:
    description:
      - Tunnel name to query.
      - If not specified, all tunnels are returned.
    type: str
"""

EXAMPLES = r"""
- name: Ensure tunnel facts are gathered
  damex.cloudflare.cloudflare_tunnel_info:
    name: hetzner
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
  register: cloudflare_tunnel_state

- name: Ensure cloudflared service
  ansible.builtin.template:
    src: cloudflared.service.j2
    dest: /etc/systemd/system/cloudflared.service
  vars:
    cloudflared_token: "{{ cloudflare_tunnel_state.tunnel.token }}"
"""

RETURN = r"""
tunnels:
  description: Tunnel information.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Tunnel unique identifier.
      returned: always
      type: str
    name:
      description: Tunnel display name.
      returned: always
      type: str
    status:
      description: Tunnel connection status.
      returned: always
      type: str
    ingress:
      description: Current ingress rules.
      returned: when querying a specific tunnel
      type: list
    token:
      description: Tunnel authentication token for cloudflared.
      returned: when querying a specific tunnel
      type: str
"""

from typing import Any

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_info_module,
    cloudflare_find_tunnel,
    cloudflare_get_tunnel_configuration,
    cloudflare_get_tunnel_token,
    cloudflare_resolve_account_id,
    cloudflare_run_info_module,
)


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

    def _gather_tunnel_information() -> None:
        with cloudflare_create_client(module) as client:
            account_id = cloudflare_resolve_account_id(
                client,
                module.params.get('account_id'),
                module.params.get('account_name'),
            )
            name = module.params.get('name')

            if name:
                tunnel = cloudflare_find_tunnel(client, account_id, name)
                if not tunnel:
                    module.exit_json(tunnels=[])
                    return
                token = cloudflare_get_tunnel_token(
                    client,
                    account_id,
                    tunnel['id'],
                )
                configuration = cloudflare_get_tunnel_configuration(
                    client,
                    account_id,
                    tunnel['id'],
                )
                tunnel['token'] = token
                tunnel['ingress'] = configuration.get('ingress', [])
                module.exit_json(tunnels=[tunnel])
                return

            response = client.get(
                f'/accounts/{account_id}/cfd_tunnel',
                params={'is_deleted': 'false'},
            )
            tunnels: list[dict[str, Any]] = response.get('result', [])
            module.exit_json(tunnels=tunnels)

    cloudflare_run_info_module(module, _gather_tunnel_information)


if __name__ == '__main__':
    main()
