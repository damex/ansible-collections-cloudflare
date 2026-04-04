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
