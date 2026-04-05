#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare DNS records for a zone.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_dns_records
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare DNS records for a zone
description:
  - 'Ensures DNS records for a Cloudflare zone using the batch API, see the docs: U(https://developers.cloudflare.com/dns/).'
  - All records for the zone are reconciled in a single API call.
  - Records are matched by type, name, and content.
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.zone
  - damex.cloudflare.common.write_attributes
  - damex.cloudflare.common.dns_records
"""

EXAMPLES = r"""
- name: Ensure DNS records for zone
  damex.cloudflare.cloudflare_dns_records:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    records:
      - record: "@"
        type: A
        content: 192.0.2.1
      - record: www
        type: CNAME
        content: example.com
        proxied: true
      - record: "@"
        type: MX
        content: mail.example.com
        priority: 10
      - record: "@"
        type: TXT
        content: v=spf1 include:_spf.example.com ~all
      - record: old
        type: A
        content: 192.0.2.99
        state: absent
"""

RETURN = r"""
posts:
  description: Records created.
  returned: success
  type: list
  elements: dict
puts:
  description: Records updated.
  returned: success
  type: list
  elements: dict
deletes:
  description: Records deleted.
  returned: success
  type: list
  elements: dict
"""

from typing import Any

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_build_record_name,
    cloudflare_create_client,
    cloudflare_create_write_module,
    cloudflare_resolve_zone_id,
    cloudflare_run_write_module,
)


def cloudflare_list_dns_records(
    client: CloudflareClient,
    zone_id: str,
) -> list[dict[str, Any]]:
    """
    List all DNS records for a zone with pagination.

    >>> cloudflare_list_dns_records(client, 'zone-id')
    [{'id': '...', 'type': 'A', 'name': 'example.com', 'content': '192.0.2.1'}]
    """
    all_records: list[dict[str, Any]] = []
    page = 1
    while True:
        response = client.get(
            f'/zones/{zone_id}/dns_records',
            params={
                'page': str(page),
                'per_page': '100',
            },
        )
        records: list[dict[str, Any]] = response.get('result', [])
        all_records.extend(records)
        result_information = response.get('result_info', {})
        total_pages = result_information.get('total_pages', 1)
        if page >= total_pages:
            break
        page = page + 1
    return all_records


def _find_current_record(
    current_records: list[dict[str, Any]],
    record_type: str,
    record_name: str,
    content: str | None,
) -> dict[str, Any] | None:
    """
    Find a matching current record by type, name, and content.

    >>> _find_current_record([{'type': 'A', 'name': 'www.e.com', 'content': '1.2.3.4'}], 'A', 'www.e.com', '1.2.3.4')
    {'type': 'A', 'name': 'www.e.com', 'content': '1.2.3.4'}
    """
    for current_record in current_records:
        if current_record.get('type') != record_type:
            continue
        if current_record.get('name') != record_name:
            continue
        if content is not None and current_record.get('content') != content:
            continue
        return current_record
    return None


def _build_record_payload(
    desired: dict[str, Any],
    record_name: str,
) -> dict[str, Any]:
    """
    Build API payload from desired record.

    >>> _build_record_payload({'type': 'A', 'content': '1.2.3.4', 'ttl': 1, 'proxied': False}, 'www.e.com')
    {'type': 'A', 'name': 'www.e.com', 'content': '1.2.3.4', 'ttl': 1, 'proxied': False}
    """
    payload: dict[str, Any] = {
        'type': desired['type'],
        'name': record_name,
        'content': desired['content'],
        'ttl': desired.get('ttl', 1),
    }
    proxied = desired.get('proxied')
    if proxied is not None:
        payload['proxied'] = proxied
    priority = desired.get('priority')
    if priority is not None:
        payload['priority'] = priority
    return payload


def _record_needs_update(
    current: dict[str, Any],
    desired_payload: dict[str, Any],
) -> bool:
    """
    Check if current record differs from desired payload.

    >>> _record_needs_update({'ttl': 1, 'proxied': False}, {'ttl': 3600, 'proxied': False})
    True
    """
    for desired_key, desired_value in desired_payload.items():
        if desired_key in ('type', 'name', 'content'):
            continue
        if current.get(desired_key) != desired_value:
            return True
    return False


def _format_record_line(record: dict[str, Any]) -> str:
    """
    Format a record as a single diff-friendly line.

    >>> _format_record_line({'type': 'A', 'name': 'www.example.com', 'content': '192.0.2.1', 'ttl': 1})
    'A www.example.com 192.0.2.1 ttl=1'
    """
    parts = [
        record.get('type', ''),
        record.get('name', ''),
        record.get('content', ''),
    ]
    ttl = record.get('ttl')
    if ttl is not None:
        parts.append(f'ttl={ttl}')
    priority = record.get('priority')
    if priority is not None:
        parts.append(f'priority={priority}')
    proxied = record.get('proxied')
    if proxied:
        parts.append('proxied=true')
    return ' '.join(parts)


def _process_desired_record(
    desired: dict[str, Any],
    current_records: list[dict[str, Any]],
    zone_name: str,
    batch: dict[str, list[Any]],
) -> None:
    """
    Process a single desired record into batch operations.

    >>> batch = {'posts': [], 'puts': [], 'deletes': [], 'before_lines': [], 'after_lines': []}
    >>> _process_desired_record({'record': 'www', 'type': 'A', 'content': '1.2.3.4'}, [], 'e.com', batch)
    """
    record_name = cloudflare_build_record_name(
        desired['record'],
        zone_name,
    )
    state = desired.get('state', 'present')
    current = _find_current_record(
        current_records,
        desired['type'],
        record_name,
        desired.get('content'),
    )

    if state == 'present':
        payload = _build_record_payload(desired, record_name)
        if not current:
            batch['posts'].append(payload)
            batch['after_lines'].append(_format_record_line(payload))
        elif _record_needs_update(current, payload):
            payload['id'] = current['id']
            batch['puts'].append(payload)
            batch['before_lines'].append(_format_record_line(current))
            batch['after_lines'].append(_format_record_line(payload))
    elif state == 'absent' and current:
        batch['deletes'].append({'id': current['id']})
        batch['before_lines'].append(_format_record_line(current))


def cloudflare_compute_dns_batch(
    desired_records: list[dict[str, Any]],
    current_records: list[dict[str, Any]],
    zone_name: str,
) -> dict[str, Any]:
    """
    Compute batch operations and diff from desired and current records.

    >>> cloudflare_compute_dns_batch([], [], 'example.com')
    {'posts': [], 'puts': [], 'deletes': [], 'diff': {'before': '', 'after': ''}}
    """
    batch: dict[str, list[Any]] = {
        'posts': [],
        'puts': [],
        'deletes': [],
        'before_lines': [],
        'after_lines': [],
    }

    for desired in desired_records:
        _process_desired_record(
            desired,
            current_records,
            zone_name,
            batch,
        )

    before_lines = batch['before_lines']
    after_lines = batch['after_lines']
    before_text = '\n'.join(sorted(before_lines)) + '\n' if before_lines else ''
    after_text = '\n'.join(sorted(after_lines)) + '\n' if after_lines else ''

    return {
        'posts': batch['posts'],
        'puts': batch['puts'],
        'deletes': batch['deletes'],
        'diff': {
            'before': before_text,
            'after': after_text,
        },
    }


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    argument_spec: dict[str, Any] = {
        'zone_id': {'type': 'str'},
        'zone_name': {'type': 'str'},
        'records': {
            'type': 'list',
            'required': True,
            'elements': 'dict',
            'options': {
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
            },
        },
    }
    module = cloudflare_create_write_module(
        argument_spec,
        required_one_of=[['zone_id', 'zone_name']],
    )

    def _ensure_dns_records() -> None:
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

            current_records = cloudflare_list_dns_records(client, zone_id)
            desired_records = module.params['records']

            batch = cloudflare_compute_dns_batch(
                desired_records,
                current_records,
                zone_name,
            )

            has_changes = batch['posts'] or batch['puts'] or batch['deletes']

            if not has_changes:
                module.exit_json(
                    changed=False,
                    posts=[],
                    puts=[],
                    deletes=[],
                )
                return

            if module.check_mode:
                module.exit_json(
                    changed=True,
                    posts=batch['posts'],
                    puts=batch['puts'],
                    deletes=batch['deletes'],
                    diff=batch['diff'],
                )
                return

            batch_payload = {
                'posts': batch['posts'],
                'puts': batch['puts'],
                'deletes': batch['deletes'],
            }
            response = client.post(
                f'/zones/{zone_id}/dns_records/batch',
                data=batch_payload,
            )
            result = response.get('result', {})

            module.exit_json(
                changed=True,
                posts=result.get('posts', []),
                puts=result.get('puts', []),
                deletes=result.get('deletes', []),
                diff=batch['diff'],
            )

    cloudflare_run_write_module(module, _ensure_dns_records)


if __name__ == '__main__':
    main()
