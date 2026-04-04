#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare zones.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_zone
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare zones
description:
  - 'Ensures Cloudflare zones using the Cloudflare API, see the docs: U(https://api.cloudflare.com/).'
extends_documentation_fragment:
  - damex.cloudflare.common
attributes:
  check_mode:
    support: full
    description: Supports check mode.
  diff_mode:
    support: none
    description: Does not support diff mode.
options:
  name:
    description:
      - Zone domain name.
    required: true
    type: str
  account_name:
    description:
      - Cloudflare account name.
    required: true
    type: str
  state:
    description:
      - Zone state.
    type: str
    choices:
      - absent
      - present
    default: present
  jump_start:
    description:
      - Zone jump start.
    type: bool
    default: false
  type:
    description:
      - Zone type.
    type: str
    choices:
      - full
      - partial
      - secondary
    default: full
  universal_ssl:
    description:
      - Universal SSL.
    type: bool
  ssl_mode:
    description:
      - SSL mode.
    type: str
    choices:
      - "off"
      - flexible
      - full
      - strict
      - origin_pull
  always_https:
    description:
      - Always HTTPS redirect.
    type: bool
  min_tls_version:
    description:
      - Minimum TLS version.
    type: str
    choices:
      - "1.0"
      - "1.1"
      - "1.2"
      - "1.3"
"""

EXAMPLES = r"""
- name: Ensure zone using API token
  damex.cloudflare.cloudflare_zone:
    name: example.com
    account_name: my-account
    api_token: "{{ cloudflare_api_token }}"
    state: present

- name: Ensure zone with jump start
  damex.cloudflare.cloudflare_zone:
    name: example.com
    account_name: my-account
    api_token: "{{ cloudflare_api_token }}"
    jump_start: true

- name: Ensure zone absent
  damex.cloudflare.cloudflare_zone:
    name: example.com
    account_name: my-account
    api_token: "{{ cloudflare_api_token }}"
    state: absent

- name: Ensure zone using legacy auth
  damex.cloudflare.cloudflare_zone:
    name: example.com
    account_name: my-account
    account_email: user@example.com
    account_api_key: "{{ cloudflare_api_key }}"
    state: present

- name: Ensure zone with security settings
  damex.cloudflare.cloudflare_zone:
    name: example.com
    account_name: my-account
    api_token: "{{ cloudflare_api_token }}"
    ssl_mode: full
    always_https: true
    min_tls_version: "1.2"
    universal_ssl: true
"""

RETURN = r"""
zone:
  description: The zone object from the Cloudflare API.
  returned: when state is present, or state is absent with check_mode
  type: dict
  contains:
    id:
      description: The zone ID.
      returned: success
      type: str
      sample: 023e105f4ecef8ad9ca31a8372d0c353
    name:
      description: The zone domain name.
      returned: success
      type: str
      sample: example.com
    status:
      description: The zone status.
      returned: success
      type: str
      sample: active
    type:
      description: The zone type.
      returned: success
      type: str
      sample: full
    account:
      description: The account the zone belongs to.
      returned: success
      type: dict
      sample: {"id": "023e105f4ecef8ad9ca31a8372d0c353", "name": "my-account"}
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
    cloudflare_get_account,
    cloudflare_run_write_module,
)


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


def cloudflare_create_zone(
    client: CloudflareClient,
    name: str,
    account_id: str,
    jump_start: bool,
    zone_type: str,
) -> dict[str, Any]:
    """
    Create a zone.

    >>> cloudflare_create_zone(client, 'example.com', 'acct-id', True, 'full')
    {'id': '...', 'name': 'example.com', 'status': 'pending', 'type': 'full'}
    """
    response = client.post(
        '/zones',
        data={
            'name': name,
            'account': {'id': account_id},
            'jump_start': jump_start,
            'type': zone_type,
        },
    )
    zone: dict[str, Any] = response.get('result', {})
    return zone


def cloudflare_delete_zone(
    client: CloudflareClient,
    zone_id: str,
) -> None:
    """
    Delete a zone by ID.

    >>> cloudflare_delete_zone(client, 'zone-id-123')
    """
    client.delete(f'/zones/{zone_id}')


def cloudflare_get_zone_setting(
    client: CloudflareClient,
    zone_id: str,
    setting_name: str,
) -> Any:
    """
    Get a zone setting value.

    >>> cloudflare_get_zone_setting(client, 'zone-id', 'ssl')
    'full'
    """
    response = client.get(f'/zones/{zone_id}/settings/{setting_name}')
    result = response.get('result', {})
    return result['value']


def cloudflare_set_zone_setting(
    client: CloudflareClient,
    zone_id: str,
    setting_name: str,
    value: Any,
) -> None:
    """
    Set a zone setting value.

    >>> cloudflare_set_zone_setting(client, 'zone-id', 'ssl', 'full')
    """
    client.patch(
        f'/zones/{zone_id}/settings/{setting_name}',
        data={'value': value},
    )


def cloudflare_get_universal_ssl(
    client: CloudflareClient,
    zone_id: str,
) -> bool:
    """
    Get Universal SSL enabled state.

    >>> cloudflare_get_universal_ssl(client, 'zone-id')
    True
    """
    response = client.get(f'/zones/{zone_id}/ssl/universal/settings')
    result = response.get('result', {})
    return bool(result['enabled'])


def cloudflare_set_universal_ssl(
    client: CloudflareClient,
    zone_id: str,
    enabled: bool,
) -> None:
    """
    Set Universal SSL enabled state.

    >>> cloudflare_set_universal_ssl(client, 'zone-id', True)
    """
    client.patch(
        f'/zones/{zone_id}/ssl/universal/settings',
        data={'enabled': enabled},
    )


def cloudflare_ensure_zone_setting(
    client: CloudflareClient,
    zone_id: str,
    setting_name: str,
    value: Any,
    check_mode: bool,
) -> bool:
    """
    Ensure a zone setting matches the desired value.

    >>> cloudflare_ensure_zone_setting(client, 'zone-id', 'ssl', 'full', False)
    True
    """
    if cloudflare_get_zone_setting(client, zone_id, setting_name) != value:
        if not check_mode:
            cloudflare_set_zone_setting(client, zone_id, setting_name, value)
        return True
    return False


def cloudflare_ensure_universal_ssl(
    client: CloudflareClient,
    zone_id: str,
    enabled: bool,
    check_mode: bool,
) -> bool:
    """
    Ensure Universal SSL matches the desired enabled state.

    >>> cloudflare_ensure_universal_ssl(client, 'zone-id', True, False)
    True
    """
    if cloudflare_get_universal_ssl(client, zone_id) != enabled:
        if not check_mode:
            cloudflare_set_universal_ssl(client, zone_id, enabled)
        return True
    return False


def cloudflare_ensure_zone_settings(
    module: AnsibleModule,
    client: CloudflareClient,
    zone_id: str,
) -> bool:
    """
    Ensure all optional zone settings match the desired state.

    >>> cloudflare_ensure_zone_settings(module, client, 'zone-id')
    False
    """
    changed = False

    universal_ssl = module.params['universal_ssl']
    if universal_ssl is not None:
        if cloudflare_ensure_universal_ssl(
            client,
            zone_id,
            universal_ssl,
            module.check_mode,
        ):
            changed = True

    ssl_mode = module.params['ssl_mode']
    if ssl_mode is not None:
        if cloudflare_ensure_zone_setting(
            client,
            zone_id,
            'ssl',
            ssl_mode,
            module.check_mode,
        ):
            changed = True

    always_https = module.params['always_https']
    if always_https is not None:
        always_https_api_value = 'on' if always_https else 'off'
        if cloudflare_ensure_zone_setting(
            client,
            zone_id,
            'always_use_https',
            always_https_api_value,
            module.check_mode,
        ):
            changed = True

    min_tls_version = module.params['min_tls_version']
    if min_tls_version is not None:
        if cloudflare_ensure_zone_setting(
            client,
            zone_id,
            'min_tls_version',
            min_tls_version,
            module.check_mode,
        ):
            changed = True

    return changed


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    argument_spec: dict[str, Any] = {
        'name': {'type': 'str', 'required': True},
        'account_name': {'type': 'str', 'required': True},
        'state': {
            'type': 'str',
            'default': 'present',
            'choices': ['absent', 'present'],
        },
        'jump_start': {'type': 'bool', 'default': False},
        'type': {
            'type': 'str',
            'default': 'full',
            'choices': ['full', 'partial', 'secondary'],
        },
        'universal_ssl': {'type': 'bool'},
        'ssl_mode': {
            'type': 'str',
            'choices': ['off', 'flexible', 'full', 'strict', 'origin_pull'],
        },
        'always_https': {'type': 'bool'},
        'min_tls_version': {
            'type': 'str',
            'choices': ['1.0', '1.1', '1.2', '1.3'],
        },
    }
    module = cloudflare_create_write_module(argument_spec)

    def _ensure_zone() -> None:
        with cloudflare_create_client(module) as client:
            name = module.params['name']
            account_name = module.params['account_name']
            state = module.params['state']

            if state == 'present':
                changed = False
                zone = cloudflare_get_zone(client, name)

                if not zone:
                    if module.check_mode:
                        module.exit_json(
                            changed=True,
                            zone={},
                        )
                        return

                    account = cloudflare_get_account(client, account_name)
                    if not account:
                        raise CloudflareClientException(
                            f"account '{account_name}' not found"
                        )

                    zone = cloudflare_create_zone(
                        client,
                        name,
                        account['id'],
                        jump_start=module.params['jump_start'],
                        zone_type=module.params['type'],
                    )
                    changed = True

                if cloudflare_ensure_zone_settings(module, client, zone['id']):
                    changed = True

                module.exit_json(
                    changed=changed,
                    zone=zone,
                )
                return

            zone = cloudflare_get_zone(client, name)
            if not zone:
                module.exit_json(changed=False)
                return

            if module.check_mode:
                module.exit_json(
                    changed=True,
                    zone=zone,
                )
                return

            cloudflare_delete_zone(client, zone['id'])
            module.exit_json(changed=True)

    cloudflare_run_write_module(module, _ensure_zone)


if __name__ == '__main__':
    main()
