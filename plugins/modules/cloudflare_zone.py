#!/usr/bin/python

# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
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
      - The domain name of the zone.
    required: true
    type: str
  account_name:
    description:
      - The name of the Cloudflare account to create the zone in.
    required: true
    type: str
  state:
    description:
      - Whether the zone should be present or absent.
    type: str
    choices:
      - absent
      - present
    default: present
  jump_start:
    description:
      - Whether to automatically fetch existing DNS records on zone creation.
    type: bool
    default: false
  type:
    description:
      - The type of zone.
    type: str
    choices:
      - full
      - partial
      - secondary
    default: full
  api_token:
    description:
      - API token for authentication.
      - Required if O(account_email) and O(account_api_key) are not provided.
      - Can be specified in E(CLOUDFLARE_TOKEN) environment variable.
    type: str
  account_email:
    description:
      - Account email for legacy authentication.
      - Required together with O(account_api_key) if O(api_token) is not provided.
    type: str
  account_api_key:
    description:
      - Account API key for legacy authentication.
      - Required together with O(account_email) if O(api_token) is not provided.
    type: str
  timeout:
    description:
      - Timeout for Cloudflare API calls.
    type: int
    default: 30
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

import json
from typing import Any
from urllib.parse import quote

from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.urls import fetch_url

CF_API = "https://api.cloudflare.com/client/v4"


class CloudflareAPI:
    """
    Client for the Cloudflare API.

    >>> api.headers["Content-Type"]
    'application/json'
    """

    def __init__(self, module: Any) -> None:
        """
        Initialize the client.

        >>> api = CloudflareAPI(module)
        >>> api.headers["Authorization"]
        'Bearer t'
        """
        self.module = module
        self.timeout: int = module.params["timeout"]
        self.headers: dict[str, str] = {}

        api_token = module.params["api_token"] or None
        account_email = module.params["account_email"]
        account_api_key = module.params["account_api_key"]

        if api_token:
            self.headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            }
        elif account_email and account_api_key:
            self.headers = {
                "X-Auth-Email": account_email,
                "X-Auth-Key": account_api_key,
                "Content-Type": "application/json",
            }
        else:
            module.fail_json(
                msg="Either api_token or both account_email"
                    " and account_api_key are required"
            )

    def _api_call(
        self,
        endpoint: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> Any:
        """
        Make an API call.

        >>> api._api_call("/zones?name=example.com")
        [{'id': '...', 'name': 'example.com', ...}]
        """
        data = json.dumps(payload) if payload else None

        resp, info = fetch_url(
            self.module,
            url=CF_API + endpoint,
            headers=self.headers,
            data=data,
            method=method,
            timeout=self.timeout,
        )

        try:
            body = resp.read()
        except AttributeError:
            body = info.get("body")

        if not body:
            self.module.fail_json(
                msg=f"Empty API response for {method} {endpoint}"
            )

        result = json.loads(
            to_text(
                body,
                errors="surrogate_or_strict",
            )
        )

        if not result.get("success"):
            errors = "; ".join(
                f"{e['code']}: {e['message']}"
                for e in result.get(
                    "errors",
                    [],
                )
            )
            self.module.fail_json(
                msg=f"API error on {method} {endpoint}: {errors}"
            )

        return result["result"]

    def get_zone(self, name: str) -> dict[str, Any] | None:
        """
        Look up a zone.

        >>> api.get_zone("example.com")
        {'id': '...', 'name': 'example.com', 'status': 'active', 'type': 'full'}
        """
        zones = self._api_call(f"/zones?name={name}")
        return next(iter(zones), None)

    def get_account(self, name: str) -> dict[str, Any] | None:
        """
        Look up an account.

        >>> api.get_account("my account")
        {'id': '...', 'name': 'my account'}
        """
        accounts = self._api_call(f"/accounts?name={quote(name)}")
        return next(iter(accounts), None)

    def create_zone(
        self,
        name: str,
        account_id: str,
        jump_start: bool = False,
        zone_type: str = "full",
    ) -> dict[str, Any]:
        """
        Create a zone.

        >>> api.create_zone(
        ...     "example.com",
        ...     "acct-id",
        ...     jump_start=True,
        ... )
        {'id': '...', 'name': 'example.com', 'status': 'pending', 'type': 'full'}
        """
        zone: dict[str, Any] = self._api_call(
            "/zones",
            "POST",
            {
                "name": name,
                "account": {"id": account_id},
                "jump_start": jump_start,
                "type": zone_type,
            },
        )
        return zone

    def delete_zone(self, zone_id: str) -> None:
        """
        Delete a Cloudflare zone by ID.

        >>> api.delete_zone("zone-id-123")
        """
        self._api_call(
            f"/zones/{zone_id}",
            "DELETE",
        )


def main() -> None:
    """
    Module entrypoint.

    >>> main()
    """
    module = AnsibleModule(
        argument_spec={
            "name": {"type": "str", "required": True},
            "account_name": {"type": "str", "required": True},
            "state": {
                "type": "str",
                "default": "present",
                "choices": ["absent", "present"],
            },
            "jump_start": {"type": "bool", "default": False},
            "type": {
                "type": "str",
                "default": "full",
                "choices": ["full", "partial", "secondary"],
            },
            "api_token": {
                "type": "str",
                "no_log": True,
                "fallback": (env_fallback, ["CLOUDFLARE_TOKEN"]),
            },
            "account_email": {"type": "str"},
            "account_api_key": {"type": "str", "no_log": True},
            "timeout": {"type": "int", "default": 30},
        },
        required_together=[
            ("account_email", "account_api_key"),
        ],
        required_one_of=[
            ["api_token", "account_api_key"],
        ],
        supports_check_mode=True,
    )

    name = module.params["name"]
    account_name = module.params["account_name"]
    state = module.params["state"]

    cf_api = CloudflareAPI(module)

    if state == "present":
        zone = cf_api.get_zone(name)
        if zone:
            module.exit_json(
                changed=False,
                zone=zone,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                zone={},
            )

        account = cf_api.get_account(account_name)
        if not account:
            module.fail_json(
                msg=f"Account '{account_name}' not found"
            )
            return

        zone = cf_api.create_zone(
            name,
            account["id"],
            jump_start=module.params["jump_start"],
            zone_type=module.params["type"],
        )
        module.exit_json(
            changed=True,
            zone=zone,
        )

    else:
        zone = cf_api.get_zone(name)
        if not zone:
            module.exit_json(changed=False)
            return

        if module.check_mode:
            module.exit_json(
                changed=True,
                zone=zone,
            )
            return

        cf_api.delete_zone(zone["id"])
        module.exit_json(changed=True)


if __name__ == "__main__":
    main()
