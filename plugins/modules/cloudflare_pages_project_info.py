#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare Pages project information is gathered.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_pages_project_info
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare Pages project information is gathered
description:
  - Gathers information about Cloudflare Pages projects.
  - Returns information about all projects or a specific project.
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.account
  - damex.cloudflare.common.info_attributes
options:
  name:
    description:
      - Project name to query.
      - If not specified, all projects are returned.
    type: str
"""

EXAMPLES = r"""
- name: Ensure Pages project information is gathered
  damex.cloudflare.cloudflare_pages_project_info:
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
  register: cloudflare_pages_project_information

- name: Ensure specific Pages project information is gathered
  damex.cloudflare.cloudflare_pages_project_info:
    name: my-docs
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
  register: cloudflare_pages_project_information
"""

RETURN = r"""
projects:
  description: Pages project information.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: Project name.
      returned: always
      type: str
    subdomain:
      description: Pages subdomain.
      returned: always
      type: str
    production_branch:
      description: Production branch.
      returned: always
      type: str
    domains:
      description: Custom domains.
      returned: always
      type: list
"""

from typing import Any

from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareNotFoundException,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_info_module,
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

    def _gather_pages_project_information() -> None:
        with cloudflare_create_client(module) as client:
            account_id = cloudflare_resolve_account_id(
                client,
                module.params.get('account_id'),
                module.params.get('account_name'),
            )
            name = module.params.get('name')

            if name:
                try:
                    response = client.get(
                        f'/accounts/{account_id}/pages/projects/{name}',
                    )
                    project = response.get('result', {})
                    module.exit_json(projects=[project] if project else [])
                except CloudflareNotFoundException:
                    module.exit_json(projects=[])
                return

            response = client.get(
                f'/accounts/{account_id}/pages/projects',
            )
            projects: list[dict[str, Any]] = response.get('result', [])
            module.exit_json(projects=projects)

    cloudflare_run_info_module(module, _gather_pages_project_information)


if __name__ == '__main__':
    main()
