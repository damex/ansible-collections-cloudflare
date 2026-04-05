#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare DNS record information is gathered.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_dns_record_info
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare DNS record information is gathered
description:
  - Gathers information about Cloudflare DNS records for a zone.
  - Returns all records or filters by type and name.
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.zone
  - damex.cloudflare.common.info_attributes
options:
  record:
    description:
      - DNS record name to filter by.
    type: str
  type:
    description:
      - DNS record type to filter by.
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
"""

EXAMPLES = r"""
- name: Ensure all DNS record information is gathered
  damex.cloudflare.cloudflare_dns_record_info:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
  register: cloudflare_dns_record_information

- name: Ensure A record information is gathered
  damex.cloudflare.cloudflare_dns_record_info:
    zone_name: example.com
    api_token: "{{ cloudflare_api_token }}"
    record: www
    type: A
  register: cloudflare_dns_record_information
"""

RETURN = r"""
records:
  description: DNS record information.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Record identifier.
      returned: always
      type: str
    type:
      description: Record type.
      returned: always
      type: str
    name:
      description: Record name.
      returned: always
      type: str
    content:
      description: Record content.
      returned: always
      type: str
    ttl:
      description: Record TTL.
      returned: always
      type: int
    proxied:
      description: Proxy status.
      returned: always
      type: bool
"""

from typing import Any

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_build_record_name,
    cloudflare_create_client,
    cloudflare_create_info_module,
    cloudflare_resolve_zone_id,
    cloudflare_run_info_module,
)


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    argument_spec: dict[str, Any] = {
        'zone_id': {'type': 'str'},
        'zone_name': {'type': 'str'},
        'record': {'type': 'str'},
        'type': {
            'type': 'str',
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
    }
    module = cloudflare_create_info_module(
        argument_spec,
        required_one_of=[['zone_id', 'zone_name']],
    )

    def _gather_dns_record_information() -> None:
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

            params: dict[str, str] = {
                'per_page': '100',
            }
            record = module.params.get('record')
            if record:
                params['name'] = cloudflare_build_record_name(
                    record,
                    zone_name,
                )
            record_type = module.params.get('type')
            if record_type:
                params['type'] = record_type

            all_records: list[dict[str, Any]] = []
            page = 1
            while True:
                params['page'] = str(page)
                response = client.get(
                    f'/zones/{zone_id}/dns_records',
                    params=params,
                )
                records: list[dict[str, Any]] = response.get('result', [])
                all_records.extend(records)
                result_information = response.get('result_info', {})
                total_pages = result_information.get('total_pages', 1)
                if page >= total_pages:
                    break
                page = page + 1

            module.exit_json(records=all_records)

    cloudflare_run_info_module(module, _gather_dns_record_information)


if __name__ == '__main__':
    main()
