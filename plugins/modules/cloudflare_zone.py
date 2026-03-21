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
requirements:
  - python3-cloudflare >= 2.11.1
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

from ansible.module_utils.basic import AnsibleModule, env_fallback

try:
    import CloudFlare
    HAS_CLOUDFLARE = True
except ImportError:
    HAS_CLOUDFLARE = False


class CloudflareAPI:
    """
    Client wrapping the CloudFlare Python library.
    """

    def __init__(self, module: Any) -> None:
        """
        Initialize the client.

        >>> api = CloudflareAPI(module)
        """
        self.module = module
        api_token = module.params["api_token"] or None
        account_email = module.params["account_email"]
        account_api_key = module.params["account_api_key"]

        if api_token:
            self.client = CloudFlare.CloudFlare(token=api_token)
        elif account_email and account_api_key:
            self.client = CloudFlare.CloudFlare(
                email=account_email,
                key=account_api_key,
            )
        else:
            module.fail_json(
                msg="Either api_token or both account_email"
                    " and account_api_key are required"
            )

    def get_zone(self, name: str) -> dict[str, Any] | None:
        """
        Look up a zone.

        >>> api.get_zone("example.com")
        {'id': '...', 'name': 'example.com', 'status': 'active', 'type': 'full'}
        """
        try:
            zones = self.client.zones.get(params={"name": name})
            return next(iter(zones), None)
        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            self.module.fail_json(msg=f"API error {int(exc)}: {exc}")
            return None

    def get_account(self, name: str) -> dict[str, Any] | None:
        """
        Look up an account.

        >>> api.get_account("my account")
        {'id': '...', 'name': 'my account'}
        """
        try:
            accounts = self.client.accounts.get(params={"name": name})
            return next(iter(accounts), None)
        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            self.module.fail_json(msg=f"API error {int(exc)}: {exc}")
            return None

    def create_zone(
        self,
        name: str,
        account_id: str,
        jump_start: bool = False,
        zone_type: str = "full",
    ) -> dict[str, Any]:
        """
        Create a zone.

        >>> api.create_zone("example.com", "acct-id", jump_start=True)
        {'id': '...', 'name': 'example.com', 'status': 'pending', 'type': 'full'}
        """
        try:
            zone: dict[str, Any] = self.client.zones.post(
                data={
                    "name": name,
                    "account": {"id": account_id},
                    "jump_start": jump_start,
                    "type": zone_type,
                },
            )
            return zone
        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            self.module.fail_json(msg=f"API error {int(exc)}: {exc}")
            return {}

    def delete_zone(self, zone_id: str) -> None:
        """
        Delete a Cloudflare zone by ID.

        >>> api.delete_zone("zone-id-123")
        """
        try:
            self.client.zones.delete(zone_id)
        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            self.module.fail_json(msg=f"API error {int(exc)}: {exc}")

    def get_zone_setting(self, zone_id: str, setting_name: str) -> Any:
        """
        Get a zone setting value.

        >>> api.get_zone_setting("zone-id", "ssl")
        'full'
        """
        try:
            result = getattr(self.client.zones.settings, setting_name).get(zone_id)
            return result["value"]
        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            self.module.fail_json(msg=f"API error {int(exc)}: {exc}")
            return None

    def set_zone_setting(
        self,
        zone_id: str,
        setting_name: str,
        value: Any,
    ) -> None:
        """
        Set a zone setting value.

        >>> api.set_zone_setting("zone-id", "ssl", "full")
        """
        try:
            getattr(self.client.zones.settings, setting_name).patch(
                zone_id,
                data={"value": value},
            )
        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            self.module.fail_json(msg=f"API error {int(exc)}: {exc}")

    def get_universal_ssl(self, zone_id: str) -> bool:
        """
        Get Universal SSL enabled state.

        >>> api.get_universal_ssl("zone-id")
        True
        """
        try:
            result = self.client.zones.ssl.universal.settings.get(zone_id)
            return bool(result["enabled"])
        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            self.module.fail_json(msg=f"API error {int(exc)}: {exc}")
            return False

    def set_universal_ssl(self, zone_id: str, enabled: bool) -> None:
        """
        Set Universal SSL enabled state.

        >>> api.set_universal_ssl("zone-id", True)
        """
        try:
            self.client.zones.ssl.universal.settings.patch(
                zone_id,
                data={"enabled": enabled},
            )
        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            self.module.fail_json(msg=f"API error {int(exc)}: {exc}")

    def ensure_zone_setting(
        self,
        zone_id: str,
        setting_name: str,
        value: Any,
    ) -> bool:
        """
        Ensure a zone setting matches the desired value.

        >>> api.ensure_zone_setting("zone-id", "ssl", "full")
        True
        """
        if self.get_zone_setting(zone_id, setting_name) != value:
            if not self.module.check_mode:
                self.set_zone_setting(zone_id, setting_name, value)
            return True
        return False

    def ensure_universal_ssl(self, zone_id: str, enabled: bool) -> bool:
        """
        Ensure Universal SSL matches the desired enabled state.

        >>> api.ensure_universal_ssl("zone-id", True)
        True
        """
        if self.get_universal_ssl(zone_id) != enabled:
            if not self.module.check_mode:
                self.set_universal_ssl(zone_id, enabled)
            return True
        return False


def _ensure_zone_settings(
    module: Any,
    cf_api: CloudflareAPI,
    zone_id: str,
) -> bool:
    """
    Ensure all optional zone settings match the desired state.

    >>> _ensure_zone_settings(module, cf_api, "zone-id")
    False
    """
    changed = False

    universal_ssl = module.params["universal_ssl"]
    if universal_ssl is not None:
        if cf_api.ensure_universal_ssl(zone_id, universal_ssl):
            changed = True

    ssl_mode = module.params["ssl_mode"]
    if ssl_mode is not None:
        if cf_api.ensure_zone_setting(zone_id, "ssl", ssl_mode):
            changed = True

    always_https = module.params["always_https"]
    if always_https is not None:
        always_https_api_value = "on" if always_https else "off"
        if cf_api.ensure_zone_setting(zone_id, "always_use_https", always_https_api_value):
            changed = True

    min_tls_version = module.params["min_tls_version"]
    if min_tls_version is not None:
        if cf_api.ensure_zone_setting(zone_id, "min_tls_version", min_tls_version):
            changed = True

    return changed


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
            "universal_ssl": {"type": "bool"},
            "ssl_mode": {
                "type": "str",
                "choices": ["off", "flexible", "full", "strict", "origin_pull"],
            },
            "always_https": {"type": "bool"},
            "min_tls_version": {
                "type": "str",
                "choices": ["1.0", "1.1", "1.2", "1.3"],
            },
        },
        required_together=[
            ("account_email", "account_api_key"),
        ],
        required_one_of=[
            ["api_token", "account_api_key"],
        ],
        supports_check_mode=True,
    )

    if not HAS_CLOUDFLARE:
        module.fail_json(msg="The 'python3-cloudflare' package is required")

    name = module.params["name"]
    account_name = module.params["account_name"]
    state = module.params["state"]

    cf_api = CloudflareAPI(module)

    if state == "present":
        changed = False
        zone = cf_api.get_zone(name)

        if not zone:
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
            changed = True

        if _ensure_zone_settings(module, cf_api, zone["id"]):
            changed = True

        module.exit_json(
            changed=changed,
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
