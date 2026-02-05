"""
This module is used to define tenacity retry mechanisms for HTTP requests.
"""

import logging
import os

import requests
from grafap._constants import DEFAULT_TIMEOUT, ODATA_NEXT_LINK, ODATA_VALUE
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_basic_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(
        (requests.exceptions.ConnectionError, requests.exceptions.Timeout)
    ),
)


@_basic_retry
def _fetch_page(url, headers, params=None, data=None):
    """
    Wrapper around requests.get that retries on RequestException.
    """
    response = requests.get(url, headers=headers, params=params, data=data, timeout=30)
    response.raise_for_status()
    return response


def _make_request(
    method: str, url: str, headers: dict, context: str, **kwargs
) -> requests.Response:
    """
    Generic HTTP request handler with consistent error handling.

    Wraps requests.request() with standardized error handling,
    logging, and timeout management.

    :param method: HTTP method (GET, POST, PATCH, DELETE, etc.)
    :type method: str
    :param url: Target URL
    :type url: str
    :param headers: HTTP headers
    :type headers: dict
    :param context: Human-readable context for error messages
    :type context: str
    :param kwargs: Additional arguments passed to requests.request()
                   (json, data, params, timeout, etc.)
    :return: Response object
    :rtype: requests.Response
    :raises Exception: For HTTP errors or general request failures
    """
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            timeout=kwargs.pop("timeout", DEFAULT_TIMEOUT),
            **kwargs,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP {e.response.status_code} error, {context}: {e}")
        raise Exception(f"HTTP {e.response.status_code} error, {context}: {e}") from e
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Connection error during {context}: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error during {context}: {e}")
        raise Exception(f"Request error during {context}: {e}") from e
    else:
        return response


def _get_paginated(
    url: str, headers: dict, params: dict | None = None, context: str = "API request"
) -> list[dict]:
    """
    Fetches paginated results from a Graph/SharePoint API endpoint.

    Automatically handles @odata.nextLink pagination and applies
    retry logic to handle transient failures.

    :param url: The initial API endpoint URL
    :type url: str
    :param headers: HTTP headers including Authorization
    :type headers: dict
    :param params: Optional query parameters
    :type params: dict | None
    :param context: Description for logging (e.g., "get lists", "fetch users")
    :type context: str
    :return: Flattened list of all results across pages
    :rtype: list[dict]
    """
    all_results = []

    while True:
        try:
            response = _make_request(
                method="GET", url=url, headers=headers, context=context, params=params
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise
        except requests.exceptions.RequestException as e:
            raise Exception(f"Pagination failed during {context}: {e}") from e

        data = response.json()
        all_results.extend(data.get(ODATA_VALUE, []))

        # Check for next page
        if ODATA_NEXT_LINK not in data:
            break

        url = data[ODATA_NEXT_LINK]

    return all_results


def _get_graph_headers(extra_headers: dict | None = None) -> dict:
    """
    Returns Graph API headers with bearer token.

    :param extra_headers: Additional headers to merge in
    :type extra_headers: dict | None
    :return: Complete headers dict for Graph API requests
    :rtype: dict
    """
    headers = {"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _get_sp_headers(extra_headers: dict | None = None) -> dict:
    """
    Returns SharePoint REST API headers with bearer token and OData format.

    :param extra_headers: Additional headers to merge in
    :type extra_headers: dict | None
    :return: Complete headers dict for SharePoint API requests
    :rtype: dict
    """
    headers = {
        "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
        "Accept": "application/json;odata=verbose;charset=utf-8",
        "Content-Type": "application/json;odata=verbose;charset=utf-8",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _check_env(key: str, default: str | None = None):
    """
    Checks if a given env var has been set. Raises an error if it hasn't been
    with instructions to read the README..md for setup instructions.
    """
    value = os.environ.get(key, default)
    if value is None:
        raise OSError(
            f"Missing required environment variable: {key}\n"
            f"Please see README.md for configuration instructions."
        )
    return value
