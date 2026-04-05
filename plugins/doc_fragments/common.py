# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Common documentation fragment for Cloudflare modules.
"""

from __future__ import annotations

__all__ = ['ModuleDocFragment']


class ModuleDocFragment:  # pylint: disable=too-few-public-methods
    """
    Common Cloudflare options.
    """

    DOCUMENTATION = r"""
options:
  api_token:
    description:
      - Cloudflare API token.
      - Required if O(account_email) and O(account_api_key) are not provided.
      - Can be specified in E(CLOUDFLARE_TOKEN) environment variable.
    type: str
  account_email:
    description:
      - Cloudflare account email.
      - Required together with O(account_api_key) if O(api_token) is not provided.
    type: str
  account_api_key:
    description:
      - Cloudflare account API key.
      - Required together with O(account_email) if O(api_token) is not provided.
    type: str
"""

    ACCOUNT = r"""
options:
  account_id:
    description:
      - Cloudflare account identifier.
      - Required if O(account_name) is not provided.
    type: str
  account_name:
    description:
      - Cloudflare account name.
      - Required if O(account_id) is not provided.
      - Resolved to account identifier via the Cloudflare API.
    type: str
"""

    DNS_RECORD = r"""
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

    DNS_RECORDS = r"""
options:
  records:
    description:
      - DNS records to ensure.
    required: true
    type: list
    elements: dict
    suboptions:
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
          - Required when O(records[].state) is C(present).
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

    ZONE = r"""
options:
  zone_id:
    description:
      - Zone identifier.
      - Required if O(zone_name) is not provided.
    type: str
  zone_name:
    description:
      - Zone domain name.
      - Required if O(zone_id) is not provided.
      - Resolved to zone identifier via the Cloudflare API.
    type: str
"""
