# -*- coding: utf-8 -*-
# Copyright: Roman Kuzmitskii <ansible@damex.org>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Cloudflare API client.
"""

from __future__ import annotations

import json
from typing import Any, NamedTuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url

__all__ = [
    'CLOUDFLARE_API_BASE_URL',
    'CloudflareClient',
    'CloudflareClientException',
    'CloudflareConnectionParameters',
    'CloudflareNotFoundException',
    'cloudflare_create_client',
]

CLOUDFLARE_API_BASE_URL = 'https://api.cloudflare.com/client/v4'


class CloudflareClientException(Exception):
    """
    API error.
    """


class CloudflareNotFoundException(CloudflareClientException):
    """
    Resource not found.
    """


class CloudflareConnectionParameters(NamedTuple):
    """
    Connection parameters for Cloudflare API.

    >>> params = CloudflareConnectionParameters(api_token='test-token')
    >>> params.api_token
    'test-token'
    """

    api_token: str | None = None
    account_email: str | None = None
    account_api_key: str | None = None


class CloudflareClient:
    """
    Cloudflare API client.
    """

    def __init__(self, parameters: CloudflareConnectionParameters) -> None:
        """
        Set connection parameters.

        >>> CloudflareClient(CloudflareConnectionParameters(api_token='test'))
        <...CloudflareClient object...>
        """
        self.parameters = parameters
        if not parameters.api_token and not (
            parameters.account_email and parameters.account_api_key
        ):
            raise CloudflareClientException(
                'either api_token or both account_email'
                ' and account_api_key are required'
            )

    def __enter__(self) -> CloudflareClient:
        """
        Enter context.

        >>> with CloudflareClient(CloudflareConnectionParameters(api_token='t')) as client:
        ...     pass
        """
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: object,
    ) -> None:
        """
        Exit context.

        >>> client.__exit__(None, None, None)
        """

    def _headers(self) -> dict[str, str]:
        """
        Build request headers.

        >>> CloudflareClient(CloudflareConnectionParameters(api_token='t'))._headers()['Authorization']
        'Bearer t'
        """
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.parameters.api_token:
            headers['Authorization'] = f'Bearer {self.parameters.api_token}'
        elif self.parameters.account_email and self.parameters.account_api_key:
            headers['X-Auth-Email'] = self.parameters.account_email
            headers['X-Auth-Key'] = self.parameters.account_api_key
        return headers

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Send request and parse response.

        >>> client._request('GET', '/zones')
        {'success': True, 'result': [...]}
        """
        url = f'{CLOUDFLARE_API_BASE_URL}{path}'
        if params:
            url = f'{url}?{urlencode(params)}'
        body = json.dumps(data).encode('utf-8') if data is not None else None
        try:
            response = open_url(
                url,
                method=method,
                data=body,
                headers=self._headers(),
            )
            content: dict[str, Any] = json.loads(response.read())
        except HTTPError as http_error:
            error_body = http_error.read()
            try:
                error_content = json.loads(error_body)
                errors = error_content.get('errors', [])
                first_error = next(iter(errors), None)
                if first_error:
                    error_code = first_error.get('code', 0)
                    error_message = first_error.get('message', 'unknown error')
                    if http_error.code == 404:
                        raise CloudflareNotFoundException(
                            f'API error {error_code}: {error_message}'
                        ) from http_error
                    raise CloudflareClientException(
                        f'API error {error_code}: {error_message}'
                    ) from http_error
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
            raise CloudflareClientException(
                f'HTTP error {http_error.code}: {http_error.reason}'
            ) from http_error
        except URLError as url_error:
            raise CloudflareClientException(
                f'connection error: {url_error.reason}'
            ) from url_error
        except Exception as exception:
            raise CloudflareClientException(str(exception)) from exception

        if not content.get('success', False):
            errors = content.get('errors', [])
            first_error = next(iter(errors), None)
            if first_error:
                error_code = first_error.get('code', 0)
                error_message = first_error.get('message', 'unknown error')
                raise CloudflareClientException(
                    f'API error {error_code}: {error_message}'
                )
            raise CloudflareClientException('unknown API error')

        return content

    def get(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        GET request.

        >>> client.get('/zones')
        {'success': True, 'result': [...]}
        """
        return self._request('GET', path, params=params)

    def post(
        self,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        POST request.

        >>> client.post('/zones', data={'name': 'example.com'})
        {'success': True, 'result': {'id': '...', 'name': 'example.com'}}
        """
        return self._request('POST', path, data=data)

    def patch(
        self,
        path: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        PATCH request.

        >>> client.patch('/zones/id/settings/ssl', data={'value': 'full'})
        {'success': True, 'result': {'id': 'ssl', 'value': 'full'}}
        """
        return self._request('PATCH', path, data=data)

    def put(
        self,
        path: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        PUT request.

        >>> client.put('/zones/id/settings', data={'items': []})
        {'success': True, 'result': {}}
        """
        return self._request('PUT', path, data=data)

    def delete(self, path: str) -> dict[str, Any]:
        """
        DELETE request.

        >>> client.delete('/zones/zone-id')
        {'success': True, 'result': {'id': 'zone-id'}}
        """
        return self._request('DELETE', path)


def cloudflare_create_client(module: AnsibleModule) -> CloudflareClient:
    """
    Create client from module parameters.

    >>> client = cloudflare_create_client(module)
    """
    return CloudflareClient(CloudflareConnectionParameters(
        api_token=module.params.get('api_token') or None,
        account_email=module.params.get('account_email'),
        account_api_key=module.params.get('account_api_key'),
    ))
