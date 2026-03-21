# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Shared fixtures and constants for cloudflare module unit tests.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, NamedTuple
from unittest.mock import MagicMock, patch

import CloudFlare as _cloudflare_sdk
import pytest

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_zone,
)

__all__ = [
    "ZONE",
    "ACCOUNT",
    "UNIVERSAL_SSL_ENABLED",
    "UNIVERSAL_SSL_DISABLED",
    "CFMock",
    "cf_mock",
]

ZONE: dict[str, Any] = {
    "id": "zone-id-123",
    "name": "example.com",
    "status": "active",
    "type": "full",
    "account": {"id": "acct-id-456", "name": "my-account"},
}

ACCOUNT: dict[str, str] = {"id": "acct-id-456", "name": "my-account"}

UNIVERSAL_SSL_ENABLED: dict[str, bool] = {"enabled": True}
UNIVERSAL_SSL_DISABLED: dict[str, bool] = {"enabled": False}


class CFMock(NamedTuple):
    """
    Container for the mocked CloudFlare client and constructor.

    >>> CFMock(client=MagicMock(), cls=MagicMock())
    CFMock(client=<MagicMock id='...'>, cls=<MagicMock id='...'>)
    """

    client: MagicMock
    cls: MagicMock


@pytest.fixture
def cf_mock() -> Generator[CFMock, None, None]:
    """
    Patch CloudFlare.CloudFlare for the test duration.

    >>> type(next(cf_mock())).__name__
    'CFMock'
    """
    with patch.object(cloudflare_zone, "CloudFlare") as mock_cf:
        mock_client = MagicMock()
        mock_cf.CloudFlare.return_value = mock_client
        mock_cf.exceptions.CloudFlareAPIError = _cloudflare_sdk.exceptions.CloudFlareAPIError
        yield CFMock(client=mock_client, cls=mock_cf.CloudFlare)
