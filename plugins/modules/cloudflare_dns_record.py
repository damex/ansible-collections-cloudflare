#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare DNS records.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_dns_record
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare DNS record
description:
  - 'Ensures Cloudflare DNS records using the Cloudflare API, see the docs: U(https://developers.cloudflare.com/dns/).'
  - Records are matched by type, name, and content for idempotency.
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
  record:
    description:
      - DNS record name (subdomain or @ for zone apex).
    required: true
    type: str
  type:
    description:
      - DNS record type.
    required: true
    type: str
    choices:
      - A
      - AAAA
      - CAA
      - CNAME
      - DS
      - HTTPS
      - MX
      - NAPTR
      - NS
      - PTR
      - SMIMEA
      - SRV
      - SSHFP
      - SVCB
      - TLSA
      - TXT
      - URI
  content:
    description:
      - DNS record content.
      - Required when O(state) is C(present).
    type: str
  ttl:
    description:
      - DNS record TTL in seconds.
      - Value of 1 means automatic.
    type: int
    default: 1
  priority:
    description:
      - DNS record priority.
      - Required for MX and URI records.
    type: int
  proxied:
    description:
      - Cloudflare proxy status.
      - Only applicable to A, AAAA, and CNAME records.
    type: bool
    default: false
  state:
    description:
      - DNS record state.
    type: str
    choices:
      - absent
      - present
    default: present
"""

EXAMPLES = r"""
- name: Ensure A record
  damex.cloudflare.cloudflare_dns_record:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    record: www
    type: A
    content: 192.0.2.1

- name: Ensure AAAA record
  damex.cloudflare.cloudflare_dns_record:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    record: www
    type: AAAA
    content: 2001:db8::1

- name: Ensure MX record
  damex.cloudflare.cloudflare_dns_record:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    record: example.com
    type: MX
    content: mail.example.com
    priority: 10

- name: Ensure CNAME record with proxy
  damex.cloudflare.cloudflare_dns_record:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    record: blog
    type: CNAME
    content: example.com
    proxied: true

- name: Ensure TXT record
  damex.cloudflare.cloudflare_dns_record:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    record: example.com
    type: TXT
    content: v=spf1 include:_spf.example.com ~all

- name: Ensure DNS record is absent
  damex.cloudflare.cloudflare_dns_record:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    record: old
    type: A
    content: 192.0.2.99
    state: absent
"""

RETURN = r"""
dns_record:
  description: DNS record object from the Cloudflare API.
  returned: when state is present
  type: dict
  contains:
    id:
      description: Record identifier.
      returned: success
      type: str
    type:
      description: Record type.
      returned: success
      type: str
    name:
      description: Record name.
      returned: success
      type: str
    content:
      description: Record content.
      returned: success
      type: str
    ttl:
      description: Record TTL.
      returned: success
      type: int
    proxied:
      description: Proxy status.
      returned: success
      type: bool
    priority:
      description: Record priority.
      returned: success
      type: int
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
    cloudflare_resolve_zone_id,
    cloudflare_run_write_module,
)


def cloudflare_find_dns_record(
    client: CloudflareClient,
    zone_id: str,
    record_type: str,
    record_name: str,
    content: str | None,
) -> dict[str, Any] | None:
    """
    Find a DNS record by type, name, and content.

    >>> cloudflare_find_dns_record(client, 'zone-id', 'A', 'www.example.com', '192.0.2.1')
    {'id': '...', 'type': 'A', 'name': 'www.example.com', 'content': '192.0.2.1'}
    """
    params: dict[str, str] = {
        'type': record_type,
        'name': record_name,
    }
    if content is not None:
        params['content'] = content
    response = client.get(
        f'/zones/{zone_id}/dns_records',
        params=params,
    )
    records: list[dict[str, Any]] = response.get('result', [])
    return next(iter(records), None)


def cloudflare_create_dns_record(
    client: CloudflareClient,
    zone_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a DNS record.

    >>> cloudflare_create_dns_record(client, 'zone-id', {'type': 'A', 'name': 'www', 'content': '192.0.2.1'})
    {'id': '...', 'type': 'A', 'name': 'www.example.com', 'content': '192.0.2.1'}
    """
    response = client.post(
        f'/zones/{zone_id}/dns_records',
        data=data,
    )
    record: dict[str, Any] = response.get('result', {})
    return record


def cloudflare_update_dns_record(
    client: CloudflareClient,
    zone_id: str,
    record_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Update a DNS record.

    >>> cloudflare_update_dns_record(client, 'zone-id', 'record-id', {'type': 'A', 'content': '192.0.2.2'})
    {'id': 'record-id', 'type': 'A', 'content': '192.0.2.2'}
    """
    response = client.put(
        f'/zones/{zone_id}/dns_records/{record_id}',
        data=data,
    )
    record: dict[str, Any] = response.get('result', {})
    return record


def cloudflare_delete_dns_record(
    client: CloudflareClient,
    zone_id: str,
    record_id: str,
) -> None:
    """
    Delete a DNS record.

    >>> cloudflare_delete_dns_record(client, 'zone-id', 'record-id')
    """
    client.delete(f'/zones/{zone_id}/dns_records/{record_id}')


def cloudflare_build_record_name(
    record: str,
    zone_name: str,
) -> str:
    """
    Build fully qualified record name.

    >>> cloudflare_build_record_name('www', 'example.com')
    'www.example.com'
    """
    if record == '@' or record == zone_name or record.endswith(f'.{zone_name}'):
        return zone_name if record == '@' else record
    return f'{record}.{zone_name}'


def _build_record_data(
    module: AnsibleModule,
    record_name: str,
) -> dict[str, Any]:
    """
    Build record payload from module parameters.

    >>> _build_record_data(module, 'www.example.com')
    {'type': 'A', 'name': 'www.example.com', 'content': '192.0.2.1', 'ttl': 1}
    """
    data: dict[str, Any] = {
        'type': module.params['type'],
        'name': record_name,
        'content': module.params['content'],
        'ttl': module.params['ttl'],
    }
    if module.params['proxied'] is not None:
        data['proxied'] = module.params['proxied']
    priority = module.params.get('priority')
    if priority is not None:
        data['priority'] = priority
    return data


def _record_needs_update(
    current: dict[str, Any],
    desired: dict[str, Any],
) -> bool:
    """
    Check if current record differs from desired state.

    >>> _record_needs_update({'ttl': 1, 'proxied': False}, {'ttl': 3600, 'proxied': False})
    True
    """
    for desired_key, desired_value in desired.items():
        if desired_key in ('type', 'name'):
            continue
        if current.get(desired_key) != desired_value:
            return True
    return False


def cloudflare_ensure_dns_record_present(
    module: AnsibleModule,
    client: CloudflareClient,
    zone_id: str,
    record_name: str,
) -> None:
    """
    Ensure DNS record is present.

    >>> cloudflare_ensure_dns_record_present(module, client, 'zone-id', 'www.example.com')
    """
    content = module.params['content']
    if content is None:
        raise CloudflareClientException('content is required when state is present')

    current = cloudflare_find_dns_record(
        client,
        zone_id,
        module.params['type'],
        record_name,
        content,
    )
    desired = _build_record_data(module, record_name)

    if not current:
        if module.check_mode:
            module.exit_json(changed=True, dns_record={})
            return
        record = cloudflare_create_dns_record(client, zone_id, desired)
        module.exit_json(
            changed=True,
            dns_record=record,
            diff={'before': {}, 'after': record},
        )
        return

    if _record_needs_update(current, desired):
        before = dict(current)
        if not module.check_mode:
            record = cloudflare_update_dns_record(
                client,
                zone_id,
                current['id'],
                desired,
            )
        else:
            record = dict(current)
            for desired_key, desired_value in desired.items():
                record[desired_key] = desired_value
        module.exit_json(
            changed=True,
            dns_record=record,
            diff={'before': before, 'after': record},
        )
        return

    module.exit_json(changed=False, dns_record=current)


def cloudflare_ensure_dns_record_absent(
    module: AnsibleModule,
    client: CloudflareClient,
    zone_id: str,
    record_name: str,
) -> None:
    """
    Ensure DNS record is absent.

    >>> cloudflare_ensure_dns_record_absent(module, client, 'zone-id', 'www.example.com')
    """
    current = cloudflare_find_dns_record(
        client,
        zone_id,
        module.params['type'],
        record_name,
        module.params.get('content'),
    )

    if not current:
        module.exit_json(changed=False)
        return

    if not module.check_mode:
        cloudflare_delete_dns_record(client, zone_id, current['id'])

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
        'zone_id': {'type': 'str'},
        'zone_name': {'type': 'str'},
        'record': {'type': 'str', 'required': True},
        'type': {
            'type': 'str',
            'required': True,
            'choices': [
                'A',
                'AAAA',
                'CAA',
                'CNAME',
                'DS',
                'HTTPS',
                'MX',
                'NAPTR',
                'NS',
                'PTR',
                'SMIMEA',
                'SRV',
                'SSHFP',
                'SVCB',
                'TLSA',
                'TXT',
                'URI',
            ],
        },
        'content': {'type': 'str'},
        'ttl': {'type': 'int', 'default': 1},
        'priority': {'type': 'int'},
        'proxied': {'type': 'bool', 'default': False},
        'state': {
            'type': 'str',
            'default': 'present',
            'choices': ['absent', 'present'],
        },
    }
    module = cloudflare_create_write_module(
        argument_spec,
        required_one_of=[['zone_id', 'zone_name']],
    )

    def _ensure_dns_record() -> None:
        with cloudflare_create_client(module) as client:
            zone_name = module.params.get('zone_name') or ''
            zone_id = cloudflare_resolve_zone_id(
                client,
                module.params.get('zone_id'),
                module.params.get('zone_name'),
            )

            if not zone_name:
                zone_response = client.get(f'/zones/{zone_id}')
                zone_name = zone_response.get('result', {}).get('name', '')

            record_name = cloudflare_build_record_name(
                module.params['record'],
                zone_name,
            )

            if module.params['state'] == 'present':
                cloudflare_ensure_dns_record_present(
                    module,
                    client,
                    zone_id,
                    record_name,
                )
            else:
                cloudflare_ensure_dns_record_absent(
                    module,
                    client,
                    zone_id,
                    record_name,
                )

    cloudflare_run_write_module(module, _ensure_dns_record)


if __name__ == '__main__':
    main()
