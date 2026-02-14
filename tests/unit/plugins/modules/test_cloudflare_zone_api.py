# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the CloudflareAPI utility class.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_zone,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    ACCOUNT,
    ZONE,
    cf_response,
)

__all__ = [
    "test_get_zone_found",
    "test_get_zone_not_found",
    "test_get_account_found",
    "test_get_account_not_found",
    "test_get_account_url_encodes_spaces",
    "test_create_zone_payload",
    "test_delete_zone_endpoint",
]


class AnsibleFailJson(Exception):
    """
    Raised by mocked fail_json.

    >>> raise AnsibleFailJson({"msg": "error"})
    Traceback (most recent call last):
        ...
    test_cloudflare_zone_api.AnsibleFailJson: {'msg': 'error'}
    """

    def __init__(self, result: dict[str, Any]) -> None:
        """
        Store result for assertion.

        >>> AnsibleFailJson({"msg": "error"}).result
        {'msg': 'error'}
        """
        super().__init__(result)
        self.result = result


def _raise_fail_json(msg: str) -> None:
    """
    Raise AnsibleFailJson with the error message.

    >>> _raise_fail_json("not found")
    Traceback (most recent call last):
        ...
    test_cloudflare_zone_api.AnsibleFailJson: {'msg': 'not found'}
    """
    raise AnsibleFailJson({"msg": msg})


def make_module(
    api_token: str,
    timeout: int,
) -> MagicMock:
    """
    Build a mock AnsibleModule for CloudflareAPI instantiation.

    >>> make_module(
    ...     api_token="t",
    ...     timeout=30,
    ... ).params["api_token"]
    't'
    """
    module = MagicMock()
    module.params = {
        "api_token": api_token,
        "timeout": timeout,
        "account_email": None,
        "account_api_key": None,
    }
    module.fail_json.side_effect = _raise_fail_json
    return module


def test_get_zone_found(fetch_url_mock: MagicMock) -> None:
    """get_zone returns the zone dict when found."""
    api = cloudflare_zone.CloudflareAPI(
        make_module(
            api_token="t",
            timeout=30,
        )
    )
    fetch_url_mock.return_value = cf_response([ZONE])
    result = api.get_zone("example.com")
    assert result is not None
    assert result["name"] == "example.com"


def test_get_zone_not_found(fetch_url_mock: MagicMock) -> None:
    """get_zone returns None when the zone does not exist."""
    api = cloudflare_zone.CloudflareAPI(
        make_module(
            api_token="t",
            timeout=30,
        )
    )
    fetch_url_mock.return_value = cf_response([])
    result = api.get_zone("example.com")
    assert result is None


def test_get_account_found(fetch_url_mock: MagicMock) -> None:
    """get_account returns the account dict when found."""
    api = cloudflare_zone.CloudflareAPI(
        make_module(
            api_token="t",
            timeout=30,
        )
    )
    fetch_url_mock.return_value = cf_response([ACCOUNT])
    result = api.get_account("my-account")
    assert result is not None
    assert result["id"] == "acct-id-456"


def test_get_account_not_found(fetch_url_mock: MagicMock) -> None:
    """get_account returns None when the account does not exist."""
    api = cloudflare_zone.CloudflareAPI(
        make_module(
            api_token="t",
            timeout=30,
        )
    )
    fetch_url_mock.return_value = cf_response([])
    result = api.get_account("missing")
    assert result is None


def test_get_account_url_encodes_spaces(fetch_url_mock: MagicMock) -> None:
    """get_account URL-encodes account names containing spaces."""
    api = cloudflare_zone.CloudflareAPI(
        make_module(
            api_token="t",
            timeout=30,
        )
    )
    fetch_url_mock.return_value = cf_response([ACCOUNT])
    api.get_account("my account")
    url = fetch_url_mock.call_args.kwargs["url"]
    assert "my%20account" in url


def test_create_zone_payload(fetch_url_mock: MagicMock) -> None:
    """create_zone sends the correct POST payload."""
    api = cloudflare_zone.CloudflareAPI(
        make_module(
            api_token="t",
            timeout=30,
        )
    )
    fetch_url_mock.return_value = cf_response(ZONE)
    api.create_zone(
        "example.com",
        "acct-id-456",
        jump_start=True,
        zone_type="partial",
    )
    payload = json.loads(fetch_url_mock.call_args.kwargs["data"])
    assert payload["name"] == "example.com"
    assert payload["account"]["id"] == "acct-id-456"
    assert payload["jump_start"] is True
    assert payload["type"] == "partial"


def test_delete_zone_endpoint(fetch_url_mock: MagicMock) -> None:
    """delete_zone calls DELETE on the correct zone endpoint."""
    api = cloudflare_zone.CloudflareAPI(
        make_module(
            api_token="t",
            timeout=30,
        )
    )
    fetch_url_mock.return_value = cf_response({"id": "zone-id-123"})
    api.delete_zone("zone-id-123")
    url = fetch_url_mock.call_args.kwargs["url"]
    method = fetch_url_mock.call_args.kwargs["method"]
    assert "zone-id-123" in url
    assert method == "DELETE"
