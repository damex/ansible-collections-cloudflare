# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Shared fixtures and constants for cloudflare module unit tests.
"""

from __future__ import annotations

import io
import json
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_zone,
)

__all__ = ["ZONE", "ACCOUNT", "cf_response", "fetch_url_mock"]

ZONE: dict[str, Any] = {
    "id": "zone-id-123",
    "name": "example.com",
    "status": "active",
    "type": "full",
    "account": {"id": "acct-id-456", "name": "my-account"},
}

ACCOUNT: dict[str, str] = {"id": "acct-id-456", "name": "my-account"}


def cf_response(
    result: Any,
    result_info: dict[str, Any] | None = None,
) -> tuple[io.BytesIO, dict[str, int]]:
    """
    Build a mock Cloudflare API response (resp, info) tuple.

    >>> _, info = cf_response([{"id": "z"}])
    >>> info["status"]
    200
    """
    body: dict[str, Any] = {"success": True, "result": result, "errors": []}
    if result_info is None:
        result_info = {
            "page": 1,
            "total_pages": 1,
            "per_page": 50,
            "count": len(result) if isinstance(result, list) else 1,
            "total_count": len(result) if isinstance(result, list) else 1,
        }
    body["result_info"] = result_info
    return (io.BytesIO(json.dumps(body).encode()), {"status": 200})


@pytest.fixture
def fetch_url_mock() -> Generator[MagicMock, None, None]:
    """
    Patch fetch_url for the test duration.

    >>> type(next(fetch_url_mock())).__name__
    'MagicMock'
    """
    with patch.object(
        cloudflare_zone,
        "fetch_url",
    ) as mock:
        yield mock
