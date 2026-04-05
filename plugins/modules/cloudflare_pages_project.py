#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Ensure Cloudflare Pages projects.
"""

from __future__ import annotations

__all__ = ["DOCUMENTATION", "EXAMPLES", "RETURN", "main"]

DOCUMENTATION = r"""
module: cloudflare_pages_project
author:
  - Roman Kuzmitskii (@damex)
short_description: Ensure Cloudflare Pages project
description:
  - 'Ensures Cloudflare Pages projects with build configuration and custom domains, see the docs: U(https://developers.cloudflare.com/pages/).'
extends_documentation_fragment:
  - damex.cloudflare.common
  - damex.cloudflare.common.account
  - damex.cloudflare.common.write_attributes
options:
  name:
    description:
      - Pages project name.
    required: true
    type: str
  state:
    description:
      - Project state.
    type: str
    choices:
      - absent
      - present
    default: present
  production_branch:
    description:
      - Production branch name.
      - Required when O(state) is C(present).
    type: str
  build_command:
    description:
      - Build command.
    type: str
  destination_directory:
    description:
      - Build output directory.
    type: str
  root_directory:
    description:
      - Project root directory.
    type: str
  domains:
    description:
      - Custom domains to assign to the project.
    type: list
    elements: str
"""

EXAMPLES = r"""
- name: Ensure Pages project
  damex.cloudflare.cloudflare_pages_project:
    name: my-docs
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
    production_branch: production
    build_command: make html
    destination_directory: build/html
    domains:
      - docs.example.com

- name: Ensure Pages project is absent
  damex.cloudflare.cloudflare_pages_project:
    name: old-project
    account_name: damex
    api_token: "{{ cloudflare_api_token }}"
    state: absent
"""

RETURN = r"""
project:
  description: Pages project object from the Cloudflare API.
  returned: when state is present
  type: dict
  contains:
    name:
      description: Project name.
      returned: success
      type: str
    subdomain:
      description: Pages subdomain.
      returned: success
      type: str
    production_branch:
      description: Production branch.
      returned: success
      type: str
    domains:
      description: Custom domains.
      returned: success
      type: list
"""

from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare_client import (
    CloudflareClient,
    CloudflareClientException,
    CloudflareNotFoundException,
)
from ansible_collections.damex.cloudflare.plugins.module_utils.cloudflare import (
    cloudflare_create_client,
    cloudflare_create_write_module,
    cloudflare_resolve_account_id,
    cloudflare_run_write_module,
)


def cloudflare_get_pages_project(
    client: CloudflareClient,
    account_id: str,
    name: str,
) -> dict[str, Any] | None:
    """
    Get a Pages project by name.

    >>> cloudflare_get_pages_project(client, 'acct-id', 'my-docs')
    {'name': 'my-docs', 'production_branch': 'production'}
    """
    try:
        response = client.get(
            f'/accounts/{account_id}/pages/projects/{name}',
        )
        project: dict[str, Any] = response.get('result', {})
        return project
    except CloudflareNotFoundException:
        return None


def cloudflare_create_pages_project(
    client: CloudflareClient,
    account_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a Pages project.

    >>> cloudflare_create_pages_project(client, 'acct-id', {'name': 'my-docs'})
    {'name': 'my-docs', 'production_branch': 'production'}
    """
    response = client.post(
        f'/accounts/{account_id}/pages/projects',
        data=data,
    )
    project: dict[str, Any] = response.get('result', {})
    return project


def cloudflare_update_pages_project(
    client: CloudflareClient,
    account_id: str,
    name: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Update a Pages project.

    >>> cloudflare_update_pages_project(client, 'acct-id', 'my-docs', {'production_branch': 'main'})
    {'name': 'my-docs', 'production_branch': 'main'}
    """
    response = client.patch(
        f'/accounts/{account_id}/pages/projects/{name}',
        data=data,
    )
    project: dict[str, Any] = response.get('result', {})
    return project


def cloudflare_delete_pages_project(
    client: CloudflareClient,
    account_id: str,
    name: str,
) -> None:
    """
    Delete a Pages project.

    >>> cloudflare_delete_pages_project(client, 'acct-id', 'my-docs')
    """
    client.delete(f'/accounts/{account_id}/pages/projects/{name}')


def cloudflare_list_pages_project_domains(
    client: CloudflareClient,
    account_id: str,
    name: str,
) -> list[str]:
    """
    List custom domains for a Pages project.

    >>> cloudflare_list_pages_project_domains(client, 'acct-id', 'my-docs')
    ['docs.example.com']
    """
    response = client.get(
        f'/accounts/{account_id}/pages/projects/{name}/domains',
    )
    domains: list[dict[str, Any]] = response.get('result', [])
    return [domain.get('name', '') for domain in domains]


def cloudflare_add_pages_project_domain(
    client: CloudflareClient,
    account_id: str,
    name: str,
    domain: str,
) -> None:
    """
    Add a custom domain to a Pages project.

    >>> cloudflare_add_pages_project_domain(client, 'acct-id', 'my-docs', 'docs.example.com')
    """
    client.post(
        f'/accounts/{account_id}/pages/projects/{name}/domains',
        data={'name': domain},
    )


def cloudflare_delete_pages_project_domain(
    client: CloudflareClient,
    account_id: str,
    name: str,
    domain: str,
) -> None:
    """
    Remove a custom domain from a Pages project.

    >>> cloudflare_delete_pages_project_domain(client, 'acct-id', 'my-docs', 'docs.example.com')
    """
    client.delete(
        f'/accounts/{account_id}/pages/projects/{name}/domains/{domain}',
    )


def _build_project_data(module: AnsibleModule) -> dict[str, Any]:
    """
    Build project payload from module parameters.

    >>> _build_project_data(module)
    {'name': 'my-docs', 'production_branch': 'production'}
    """
    data: dict[str, Any] = {
        'name': module.params['name'],
        'production_branch': module.params['production_branch'],
    }
    build_config: dict[str, str] = {}
    build_command = module.params.get('build_command')
    if build_command is not None:
        build_config['build_command'] = build_command
    destination_directory = module.params.get('destination_directory')
    if destination_directory is not None:
        build_config['destination_dir'] = destination_directory
    root_directory = module.params.get('root_directory')
    if root_directory is not None:
        build_config['root_dir'] = root_directory
    if build_config:
        data['build_config'] = build_config
    return data


def _project_needs_update(
    current: dict[str, Any],
    desired: dict[str, Any],
) -> bool:
    """
    Check if project needs updating.

    >>> _project_needs_update({'production_branch': 'main'}, {'production_branch': 'prod'})
    True
    """
    if current.get('production_branch') != desired.get('production_branch'):
        return True
    current_build = current.get('build_config', {})
    desired_build = desired.get('build_config', {})
    for build_key, build_value in desired_build.items():
        if current_build.get(build_key) != build_value:
            return True
    return False


def _ensure_domains(
    client: CloudflareClient,
    account_id: str,
    name: str,
    desired_domains: list[str],
    check_mode: bool,
) -> bool:
    """
    Ensure custom domains match desired state.

    >>> _ensure_domains(client, 'acct-id', 'my-docs', ['docs.example.com'], False)
    False
    """
    current_domains = cloudflare_list_pages_project_domains(
        client,
        account_id,
        name,
    )
    domains_to_add = [
        domain for domain in desired_domains
        if domain not in current_domains
    ]
    domains_to_remove = [
        domain for domain in current_domains
        if domain not in desired_domains
    ]

    if not domains_to_add and not domains_to_remove:
        return False

    if not check_mode:
        for domain in domains_to_add:
            cloudflare_add_pages_project_domain(
                client,
                account_id,
                name,
                domain,
            )
        for domain in domains_to_remove:
            cloudflare_delete_pages_project_domain(
                client,
                account_id,
                name,
                domain,
            )
    return True


def cloudflare_ensure_pages_project_present(
    module: AnsibleModule,
    client: CloudflareClient,
    account_id: str,
) -> None:
    """
    Ensure Pages project is present.

    >>> cloudflare_ensure_pages_project_present(module, client, 'acct-id')
    """
    name = module.params['name']
    production_branch = module.params.get('production_branch')
    if not production_branch:
        raise CloudflareClientException(
            'production_branch is required when state is present'
        )

    desired = _build_project_data(module)
    current = cloudflare_get_pages_project(client, account_id, name)
    desired_domains = module.params.get('domains') or []

    if not current:
        if module.check_mode:
            module.exit_json(changed=True, project={})
            return
        project = cloudflare_create_pages_project(client, account_id, desired)
        if desired_domains:
            _ensure_domains(
                client,
                account_id,
                name,
                desired_domains,
                False,
            )
        project['domains'] = desired_domains
        module.exit_json(
            changed=True,
            project=project,
            diff={'before': {}, 'after': project},
        )
        return

    changed = False
    if _project_needs_update(current, desired):
        if not module.check_mode:
            current = cloudflare_update_pages_project(
                client,
                account_id,
                name,
                desired,
            )
        changed = True

    if desired_domains:
        if _ensure_domains(
            client,
            account_id,
            name,
            desired_domains,
            module.check_mode,
        ):
            changed = True

    if changed:
        current['domains'] = desired_domains
        module.exit_json(
            changed=True,
            project=current,
        )
        return

    current['domains'] = cloudflare_list_pages_project_domains(
        client,
        account_id,
        name,
    )
    module.exit_json(changed=False, project=current)


def cloudflare_ensure_pages_project_absent(
    module: AnsibleModule,
    client: CloudflareClient,
    account_id: str,
) -> None:
    """
    Ensure Pages project is absent.

    >>> cloudflare_ensure_pages_project_absent(module, client, 'acct-id')
    """
    name = module.params['name']
    current = cloudflare_get_pages_project(client, account_id, name)

    if not current:
        module.exit_json(changed=False)
        return

    if not module.check_mode:
        cloudflare_delete_pages_project(client, account_id, name)

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
        'account_id': {'type': 'str'},
        'account_name': {'type': 'str'},
        'state': {
            'type': 'str',
            'default': 'present',
            'choices': ['absent', 'present'],
        },
        'production_branch': {'type': 'str'},
        'build_command': {'type': 'str'},
        'destination_directory': {'type': 'str'},
        'root_directory': {'type': 'str'},
        'domains': {
            'type': 'list',
            'elements': 'str',
        },
    }
    module = cloudflare_create_write_module(
        argument_spec,
        required_one_of=[['account_id', 'account_name']],
    )

    def _ensure_pages_project() -> None:
        with cloudflare_create_client(module) as client:
            account_id = cloudflare_resolve_account_id(
                client,
                module.params.get('account_id'),
                module.params.get('account_name'),
            )

            if module.params['state'] == 'present':
                cloudflare_ensure_pages_project_present(
                    module,
                    client,
                    account_id,
                )
            else:
                cloudflare_ensure_pages_project_absent(
                    module,
                    client,
                    account_id,
                )

    cloudflare_run_write_module(module, _ensure_pages_project)


if __name__ == '__main__':
    main()
