#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare email routing.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_email_routing
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare email routing
description:
  - 'Ensures Cloudflare email routing is enabled or disabled for a zone, see the docs: U(https://developers.cloudflare.com/email-routing/).'
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.zone
attributes:
  check_mode:
    support: full
    description: Supports check mode.
  diff_mode:
    support: full
    description: Supports diff mode.
options:
  enabled:
    description:
      - Email routing enabled state.
    required: true
    type: bool
"""

EXAMPLES = r"""
- name: Ensure email routing is enabled
  damex.cloudflare.cloudflare_email_routing:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    enabled: true

- name: Ensure email routing is disabled
  damex.cloudflare.cloudflare_email_routing:
    zone_id: 023e105f4ecef8ad9ca31a8372d0c353
    api_token: "{{ cloudflare_api_token }}"
    enabled: false
"""

RETURN = r"""
email_routing:
  description: Email routing settings from the Cloudflare API.
  returned: success
  type: dict
  contains:
    id:
      description: Settings identifier.
      returned: success
      type: str
    enabled:
      description: Email routing enabled state.
      returned: success
      type: bool
    name:
      description: Zone domain name.
      returned: success
      type: str
    status:
      description: Email routing status.
      returned: success
      type: str
      sample: ready
"""

from typing import Any

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_write_module,
    cloudflare_resolve_zone_id,
    cloudflare_run_write_module,
)


def cloudflare_get_email_routing(
    client: CloudflareClient,
    zone_id: str,
) -> dict[str, Any]:
    """
    Get email routing settings.

    >>> cloudflare_get_email_routing(client, 'zone-id')
    {'id': '...', 'enabled': True, 'name': 'example.com', 'status': 'ready'}
    """
    response = client.get(f'/zones/{zone_id}/email/routing')
    settings: dict[str, Any] = response.get('result', {})
    return settings


def cloudflare_enable_email_routing(
    client: CloudflareClient,
    zone_id: str,
) -> dict[str, Any]:
    """
    Enable email routing.

    >>> cloudflare_enable_email_routing(client, 'zone-id')
    {'id': '...', 'enabled': True, 'status': 'ready'}
    """
    response = client.post(f'/zones/{zone_id}/email/routing/enable')
    settings: dict[str, Any] = response.get('result', {})
    return settings


def cloudflare_disable_email_routing(
    client: CloudflareClient,
    zone_id: str,
) -> dict[str, Any]:
    """
    Disable email routing.

    >>> cloudflare_disable_email_routing(client, 'zone-id')
    {'id': '...', 'enabled': False, 'status': 'unconfigured'}
    """
    response = client.post(f'/zones/{zone_id}/email/routing/disable')
    settings: dict[str, Any] = response.get('result', {})
    return settings


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    argument_spec: dict[str, Any] = {
        'zone_id': {'type': 'str'},
        'zone_name': {'type': 'str'},
        'enabled': {'type': 'bool', 'required': True},
    }
    module = cloudflare_create_write_module(
        argument_spec,
        required_one_of=[['zone_id', 'zone_name']],
    )

    def _ensure_email_routing() -> None:
        with cloudflare_create_client(module) as client:
            zone_id = cloudflare_resolve_zone_id(
                client,
                module.params.get('zone_id'),
                module.params.get('zone_name'),
            )
            desired_enabled = module.params['enabled']

            settings = cloudflare_get_email_routing(client, zone_id)
            current_enabled = settings.get('enabled', False)

            if current_enabled == desired_enabled:
                module.exit_json(
                    changed=False,
                    email_routing=settings,
                )
                return

            if module.check_mode:
                after = dict(settings)
                after['enabled'] = desired_enabled
                module.exit_json(
                    changed=True,
                    email_routing=after,
                    diff={
                        'before': settings,
                        'after': after,
                    },
                )
                return

            if desired_enabled:
                updated = cloudflare_enable_email_routing(client, zone_id)
            else:
                updated = cloudflare_disable_email_routing(client, zone_id)

            module.exit_json(
                changed=True,
                email_routing=updated,
                diff={
                    'before': settings,
                    'after': updated,
                },
            )

    cloudflare_run_write_module(module, _ensure_email_routing)


if __name__ == '__main__':
    main()
