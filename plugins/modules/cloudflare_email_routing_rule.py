#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare email routing rules.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_email_routing_rule
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare email routing rule
description:
  - 'Ensures Cloudflare email routing rules, see the docs: U(https://developers.cloudflare.com/email-routing/).'
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.zone
  - damex.cloudflare.common.write_attributes
options:
  name:
    description:
      - Rule name.
    required: true
    type: str
  state:
    description:
      - Rule state.
    type: str
    choices:
      - absent
      - present
    default: present
  enabled:
    description:
      - Rule enabled state.
    type: bool
    default: true
  priority:
    description:
      - Rule execution priority.
      - Lower values execute first.
    type: int
  matchers:
    description:
      - Matching patterns for incoming email.
    type: list
    elements: dict
    suboptions:
      type:
        description:
          - Matcher type.
        required: true
        type: str
        choices:
          - all
          - literal
      field:
        description:
          - Matcher field.
          - Required when type is literal.
        type: str
        choices:
          - to
      value:
        description:
          - Matcher value.
          - Required when type is literal.
        type: str
  actions:
    description:
      - Actions to take on matched email.
    type: list
    elements: dict
    suboptions:
      type:
        description:
          - Action type.
        required: true
        type: str
        choices:
          - drop
          - forward
          - worker
      value:
        description:
          - Action destination addresses.
          - Required when type is forward or worker.
        type: list
        elements: str
"""

EXAMPLES = r"""
- name: Ensure catch-all forwarding rule
  damex.cloudflare.cloudflare_email_routing_rule:
    name: catch-all
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    matchers:
      - type: all
    actions:
      - type: forward
        value:
          - user@gmail.com

- name: Ensure specific address forwarding rule
  damex.cloudflare.cloudflare_email_routing_rule:
    name: admin forwarding
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    matchers:
      - type: literal
        field: to
        value: admin@example.com
    actions:
      - type: forward
        value:
          - admin@gmail.com

- name: Ensure drop rule
  damex.cloudflare.cloudflare_email_routing_rule:
    name: drop spam
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    matchers:
      - type: literal
        field: to
        value: spam@example.com
    actions:
      - type: drop

- name: Ensure rule is absent
  damex.cloudflare.cloudflare_email_routing_rule:
    name: old-rule
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    state: absent
"""

RETURN = r"""
rule:
  description: Routing rule object from the Cloudflare API.
  returned: when state is present
  type: dict
  contains:
    id:
      description: Rule identifier.
      returned: success
      type: str
    name:
      description: Rule name.
      returned: success
      type: str
    enabled:
      description: Rule enabled state.
      returned: success
      type: bool
    priority:
      description: Rule execution priority.
      returned: success
      type: int
    matchers:
      description: Matching patterns.
      returned: success
      type: list
    actions:
      description: Actions to take on matched email.
      returned: success
      type: list
"""

from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_write_module,
    cloudflare_resolve_zone_id,
    cloudflare_run_write_module,
)


def cloudflare_find_email_routing_rule(
    client: CloudflareClient,
    zone_id: str,
    matchers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Find a routing rule by matchers.

    >>> cloudflare_find_email_routing_rule(client, 'zone-id', [{'type': 'all'}])
    {'id': '...', 'name': 'catch-all', 'enabled': True}
    """
    response = client.get(f'/zones/{zone_id}/email/routing/rules')
    rules: list[dict[str, Any]] = response.get('result', [])
    for rule in rules:
        if rule.get('matchers') == matchers:
            return rule
    return None


def _strip_none_values(data: Any) -> Any:
    """
    Recursively strip None values from dicts and lists.

    >>> _strip_none_values({'type': 'all', 'field': None})
    {'type': 'all'}
    """
    if isinstance(data, dict):
        return {
            strip_key: _strip_none_values(strip_value)
            for strip_key, strip_value in data.items()
            if strip_value is not None
        }
    if isinstance(data, list):
        return [_strip_none_values(strip_item) for strip_item in data]
    return data


def _build_rule_data(module: AnsibleModule) -> dict[str, Any]:
    """
    Build rule payload from module parameters.

    >>> _build_rule_data(module)
    {'name': 'catch-all', 'enabled': True, 'matchers': [...], 'actions': [...]}
    """
    data: dict[str, Any] = {
        'name': module.params['name'],
        'enabled': module.params['enabled'],
        'matchers': _strip_none_values(module.params['matchers']),
        'actions': _strip_none_values(module.params['actions']),
    }
    priority = module.params.get('priority')
    if priority is not None:
        data['priority'] = priority
    return data


def _rules_match(
    current: dict[str, Any],
    desired: dict[str, Any],
) -> bool:
    """
    Check if current rule matches desired state.

    >>> _rules_match({'name': 'a', 'enabled': True}, {'name': 'a', 'enabled': True})
    True
    """
    for desired_key, desired_value in desired.items():
        if current.get(desired_key) != desired_value:
            return False
    return True


def cloudflare_create_email_routing_rule(
    client: CloudflareClient,
    zone_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a routing rule.

    >>> cloudflare_create_email_routing_rule(client, 'zone-id', {'name': 'r'})
    {'id': '...', 'name': 'r', 'enabled': True}
    """
    response = client.post(
        f'/zones/{zone_id}/email/routing/rules',
        data=data,
    )
    rule: dict[str, Any] = response.get('result', {})
    return rule


def cloudflare_update_email_routing_rule(
    client: CloudflareClient,
    zone_id: str,
    rule_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Update a routing rule.

    >>> cloudflare_update_email_routing_rule(client, 'zone-id', 'rule-id', {'name': 'r'})
    {'id': 'rule-id', 'name': 'r', 'enabled': True}
    """
    response = client.put(
        f'/zones/{zone_id}/email/routing/rules/{rule_id}',
        data=data,
    )
    rule: dict[str, Any] = response.get('result', {})
    return rule


def cloudflare_delete_email_routing_rule(
    client: CloudflareClient,
    zone_id: str,
    rule_id: str,
) -> None:
    """
    Delete a routing rule.

    >>> cloudflare_delete_email_routing_rule(client, 'zone-id', 'rule-id')
    """
    client.delete(f'/zones/{zone_id}/email/routing/rules/{rule_id}')


def cloudflare_ensure_email_routing_rule_present(
    module: AnsibleModule,
    client: CloudflareClient,
    zone_id: str,
) -> None:
    """
    Ensure routing rule is present.

    >>> cloudflare_ensure_email_routing_rule_present(module, client, 'zone-id')
    """
    desired = _build_rule_data(module)
    current = cloudflare_find_email_routing_rule(
        client,
        zone_id,
        desired['matchers'],
    )

    if not current:
        if module.check_mode:
            module.exit_json(changed=True, rule={})
            return
        rule = cloudflare_create_email_routing_rule(client, zone_id, desired)
        module.exit_json(
            changed=True,
            rule=rule,
            diff={'before': {}, 'after': rule},
        )
        return

    if _rules_match(current, desired):
        module.exit_json(changed=False, rule=current)
        return

    if module.check_mode:
        after = dict(current)
        for desired_key, desired_value in desired.items():
            after[desired_key] = desired_value
        module.exit_json(
            changed=True,
            rule=after,
            diff={'before': current, 'after': after},
        )
        return

    rule = cloudflare_update_email_routing_rule(
        client,
        zone_id,
        current['id'],
        desired,
    )
    module.exit_json(
        changed=True,
        rule=rule,
        diff={'before': current, 'after': rule},
    )


def cloudflare_ensure_email_routing_rule_absent(
    module: AnsibleModule,
    client: CloudflareClient,
    zone_id: str,
) -> None:
    """
    Ensure routing rule is absent.

    >>> cloudflare_ensure_email_routing_rule_absent(module, client, 'zone-id')
    """
    matchers = _strip_none_values(module.params['matchers'])
    current = cloudflare_find_email_routing_rule(
        client,
        zone_id,
        matchers,
    )

    if not current:
        module.exit_json(changed=False)
        return

    if not module.check_mode:
        cloudflare_delete_email_routing_rule(client, zone_id, current['id'])

    module.exit_json(
        changed=True,
        diff={'before': current, 'after': {}},
    )


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    argument_spec: dict[str, Any] = {
        'name': {'type': 'str', 'required': True},
        'zone_id': {'type': 'str'},
        'zone_name': {'type': 'str'},
        'state': {
            'type': 'str',
            'default': 'present',
            'choices': ['absent', 'present'],
        },
        'enabled': {'type': 'bool', 'default': True},
        'priority': {'type': 'int'},
        'matchers': {
            'type': 'list',
            'elements': 'dict',
            'options': {
                'type': {
                    'type': 'str',
                    'required': True,
                    'choices': ['all', 'literal'],
                },
                'field': {
                    'type': 'str',
                    'choices': ['to'],
                },
                'value': {'type': 'str'},
            },
        },
        'actions': {
            'type': 'list',
            'elements': 'dict',
            'options': {
                'type': {
                    'type': 'str',
                    'required': True,
                    'choices': ['drop', 'forward', 'worker'],
                },
                'value': {
                    'type': 'list',
                    'elements': 'str',
                },
            },
        },
    }
    module = cloudflare_create_write_module(
        argument_spec,
        required_one_of=[['zone_id', 'zone_name']],
    )

    def _ensure_email_routing_rule() -> None:
        with cloudflare_create_client(module) as client:
            zone_id = cloudflare_resolve_zone_id(
                client,
                module.params.get('zone_id'),
                module.params.get('zone_name'),
            )

            if module.params['state'] == 'present':
                cloudflare_ensure_email_routing_rule_present(
                    module,
                    client,
                    zone_id,
                )
            else:
                cloudflare_ensure_email_routing_rule_absent(
                    module,
                    client,
                    zone_id,
                )

    cloudflare_run_write_module(module, _ensure_email_routing_rule)


if __name__ == '__main__':
    main()
