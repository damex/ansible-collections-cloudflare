# Copyright (c) 2026 Roman Kuzmitskii <ansible@damex.org>
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the cloudflare_zone module.
"""

from __future__ import annotations

import io
import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.damex.cloudflare.plugins.modules import (
    cloudflare_zone,
)
from ansible_collections.damex.cloudflare.tests.unit.plugins.modules.conftest import (
    ACCOUNT,
    ZONE,
    cf_response,
)

__all__ = [
    "test_missing_params",
    "test_present_zone_exists",
    "test_present_zone_created",
    "test_present_verify_payload",
    "test_present_account_not_found",
    "test_present_check_mode",
    "test_absent_zone_exists",
    "test_absent_zone_missing",
    "test_absent_check_mode",
    "test_token_auth_header",
    "test_legacy_auth_headers",
    "test_api_error_response",
    "test_empty_body_response",
    "test_env_token_fallback",
    "test_empty_api_token",
]


class AnsibleExitJson(Exception):
    """
    Raised by mocked exit_json.

    >>> raise AnsibleExitJson({"changed": False})
    Traceback (most recent call last):
        ...
    test_cloudflare_zone.AnsibleExitJson: {'changed': False}
    """

    def __init__(self, result: dict[str, Any]) -> None:
        """
        Store result for assertion.

        >>> AnsibleExitJson({"changed": False}).result
        {'changed': False}
        """
        super().__init__(result)
        self.result = result


class AnsibleFailJson(Exception):
    """
    Raised by mocked fail_json.

    >>> raise AnsibleFailJson({"msg": "error"})
    Traceback (most recent call last):
        ...
    test_cloudflare_zone.AnsibleFailJson: {'msg': 'error'}
    """

    def __init__(self, result: dict[str, Any]) -> None:
        """
        Store result for assertion.

        >>> AnsibleFailJson({"msg": "error"}).result
        {'msg': 'error'}
        """
        super().__init__(result)
        self.result = result


def _raise_exit_json(
    module_instance: AnsibleModule,
    changed: bool,
    zone: dict[str, Any] | None = None,
) -> None:
    """
    Raise AnsibleExitJson with the result fields.

    >>> _raise_exit_json(module, changed=False, zone={"name": "example.com"})
    Traceback (most recent call last):
        ...
    test_cloudflare_zone.AnsibleExitJson: {'changed': False, 'zone': {'name': 'example.com'}}
    """
    raise AnsibleExitJson({"changed": changed, "zone": zone})


def _raise_fail_json(
    module_instance: AnsibleModule,
    msg: str,
) -> None:
    """
    Raise AnsibleFailJson with the error message.

    >>> _raise_fail_json(module, msg="not found")
    Traceback (most recent call last):
        ...
    test_cloudflare_zone.AnsibleFailJson: {'msg': 'not found'}
    """
    raise AnsibleFailJson({"msg": msg})


@contextmanager
def set_module_args(args: dict[str, Any]) -> Generator[None, None, None]:
    """
    Set module arguments and patch AnsibleModule for testing.

    >>> with set_module_args({"name": "example.com", "api_token": "t"}):
    ...     pass
    """
    args.setdefault("_ansible_remote_tmp", "/tmp")
    args.setdefault("_ansible_keep_remote_files", False)
    serialized = to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args}))
    with (
        patch(
            "ansible.module_utils.basic._ANSIBLE_ARGS",
            serialized,
        ),
        patch(
            "ansible.module_utils.basic._ANSIBLE_PROFILE",
            "legacy",
        ),
        patch.multiple(
            AnsibleModule,
            exit_json=_raise_exit_json,
            fail_json=_raise_fail_json,
        ),
    ):
        yield


ARGS: dict[str, str] = {
    "name": "example.com",
    "account_name": "my-account",
    "api_token": "test-token",
}


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"name": "example.com", "account_name": "my-account"},
        {"account_name": "my-account", "api_token": "t"},
        {"name": "example.com", "api_token": "t"},
        {"name": "example.com", "account_name": "a", "account_email": "u@e.com"},
    ],
)
def test_missing_params(args: dict[str, Any]) -> None:
    """Module fails with incomplete parameters."""
    with set_module_args(args):
        with pytest.raises(AnsibleFailJson):
            cloudflare_zone.main()


def test_present_zone_exists(fetch_url_mock: MagicMock) -> None:
    """Existing zone — no change."""
    with set_module_args(dict(ARGS)):
        fetch_url_mock.return_value = cf_response([ZONE])
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result["changed"] is False
    assert exc.value.result["zone"]["name"] == "example.com"


def test_present_zone_created(fetch_url_mock: MagicMock) -> None:
    """Missing zone — create it."""
    with set_module_args(dict(ARGS)):
        fetch_url_mock.side_effect = [
            cf_response([]),
            cf_response([ACCOUNT]),
            cf_response(ZONE),
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result["changed"] is True
    assert fetch_url_mock.call_count == 3


def test_present_verify_payload(fetch_url_mock: MagicMock) -> None:
    """Verify POST payload for zone creation."""
    args: dict[str, Any] = {
        "name": "example.com",
        "account_name": "my-account",
        "api_token": "test-token",
        "jump_start": True,
        "type": "partial",
    }
    with set_module_args(args):
        fetch_url_mock.side_effect = [
            cf_response([]),
            cf_response([ACCOUNT]),
            cf_response(ZONE),
        ]
        with pytest.raises(AnsibleExitJson):
            cloudflare_zone.main()
    payload = json.loads(fetch_url_mock.call_args.kwargs["data"])
    assert payload["name"] == "example.com"
    assert payload["jump_start"] is True
    assert payload["type"] == "partial"


def test_present_account_not_found(fetch_url_mock: MagicMock) -> None:
    """Missing account — fail."""
    with set_module_args(dict(ARGS)):
        fetch_url_mock.side_effect = [cf_response([]), cf_response([])]
        with pytest.raises(AnsibleFailJson) as exc:
            cloudflare_zone.main()
    assert "not found" in exc.value.result["msg"]


def test_present_check_mode(fetch_url_mock: MagicMock) -> None:
    """Check mode — changed=True, no create call."""
    with set_module_args({
        "name": "example.com",
        "account_name": "my-account",
        "api_token": "test-token",
        "_ansible_check_mode": True,
    }):
        fetch_url_mock.return_value = cf_response([])
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result["changed"] is True
    assert fetch_url_mock.call_count == 1


def test_absent_zone_exists(fetch_url_mock: MagicMock) -> None:
    """Zone exists — delete it."""
    with set_module_args({
        "name": "example.com",
        "account_name": "my-account",
        "api_token": "test-token",
        "state": "absent",
    }):
        fetch_url_mock.side_effect = [
            cf_response([ZONE]),
            cf_response({"id": ZONE["id"]}),
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result["changed"] is True


def test_absent_zone_missing(fetch_url_mock: MagicMock) -> None:
    """Zone missing — no change."""
    with set_module_args({
        "name": "example.com",
        "account_name": "my-account",
        "api_token": "test-token",
        "state": "absent",
    }):
        fetch_url_mock.return_value = cf_response([])
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result["changed"] is False


def test_absent_check_mode(fetch_url_mock: MagicMock) -> None:
    """Check mode — changed=True, no delete call."""
    args: dict[str, Any] = {
        "name": "example.com",
        "account_name": "my-account",
        "api_token": "test-token",
        "state": "absent",
        "_ansible_check_mode": True,
    }
    with set_module_args(args):
        fetch_url_mock.return_value = cf_response([ZONE])
        with pytest.raises(AnsibleExitJson) as exc:
            cloudflare_zone.main()
    assert exc.value.result["changed"] is True
    assert fetch_url_mock.call_count == 1


def test_token_auth_header(fetch_url_mock: MagicMock) -> None:
    """Bearer token header is set."""
    with set_module_args(dict(ARGS)):
        fetch_url_mock.return_value = cf_response([ZONE])
        with pytest.raises(AnsibleExitJson):
            cloudflare_zone.main()
    headers = fetch_url_mock.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-token"


def test_legacy_auth_headers(fetch_url_mock: MagicMock) -> None:
    """X-Auth-Email and X-Auth-Key headers are set."""
    args: dict[str, str] = {
        "name": "example.com",
        "account_name": "my-account",
        "account_email": "u@e.com",
        "account_api_key": "legacy-key",
    }
    with set_module_args(args):
        fetch_url_mock.return_value = cf_response([ZONE])
        with pytest.raises(AnsibleExitJson):
            cloudflare_zone.main()
    headers = fetch_url_mock.call_args.kwargs["headers"]
    assert headers["X-Auth-Email"] == "u@e.com"
    assert headers["X-Auth-Key"] == "legacy-key"


def test_api_error_response(fetch_url_mock: MagicMock) -> None:
    """API returns success=false — fail_json with code and message."""
    body: dict[str, Any] = {
        "success": False,
        "errors": [{"code": 1003, "message": "Invalid token"}],
        "result": None,
    }
    with set_module_args(dict(ARGS)):
        fetch_url_mock.return_value = (
            io.BytesIO(json.dumps(body).encode()),
            {"status": 400},
        )
        with pytest.raises(AnsibleFailJson) as exc:
            cloudflare_zone.main()
    assert "1003" in exc.value.result["msg"]
    assert "Invalid token" in exc.value.result["msg"]


def test_empty_body_response(fetch_url_mock: MagicMock) -> None:
    """Empty API response body — fail_json with empty body message."""
    with set_module_args(dict(ARGS)):
        fetch_url_mock.return_value = (None, {})
        with pytest.raises(AnsibleFailJson) as exc:
            cloudflare_zone.main()
    assert "Empty API response" in exc.value.result["msg"]


def test_env_token_fallback(fetch_url_mock: MagicMock) -> None:
    """CLOUDFLARE_TOKEN environment variable is used when api_token is absent."""
    args: dict[str, str] = {"name": "example.com", "account_name": "my-account"}
    with set_module_args(args):
        with patch.dict(
            os.environ,
            {"CLOUDFLARE_TOKEN": "env-token"},
        ):
            fetch_url_mock.return_value = cf_response([ZONE])
            with pytest.raises(AnsibleExitJson) as exc:
                cloudflare_zone.main()
    assert exc.value.result["changed"] is False
    headers = fetch_url_mock.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer env-token"


def test_empty_api_token() -> None:
    """Empty string api_token is treated as missing and fails auth."""
    with set_module_args({
        "name": "example.com",
        "account_name": "my-account",
        "api_token": "",
    }):
        with pytest.raises(AnsibleFailJson) as exc:
            cloudflare_zone.main()
    assert "api_token" in exc.value.result["msg"] or "account_email" in exc.value.result["msg"]
