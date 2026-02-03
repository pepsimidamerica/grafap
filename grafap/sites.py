"""
The sites module provides functions for getting data on the high-level sharepoint
site structure of a given tenant. Needed to retrieve a given site ID for
lower-level operations.
"""

import logging
import os

import requests
from grafap._auth import Decorators
from grafap._constants import DEFAULT_TIMEOUT, ODATA_NEXT_LINK, ODATA_VALUE
from grafap._helpers import _basic_retry, _check_env, _get_graph_headers

logger = logging.getLogger(__name__)


@Decorators._refresh_graph_token
def sites_return() -> dict:
    """
    Gets all site data in a given tenant.
    """
    _check_env("GRAPH_BASE_URL")

    @_basic_retry
    def recurs_get(url, headers):
        """
        Recursive function to handle pagination.
        """
        try:
            response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error {e.response.status_code}, could not get sharepoint site data: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not get sharepoint site data: {e}"
            ) from e
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Error, could not connect to sharepoint site data: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not get sharepoint site data: {e}")
            raise Exception(f"Error, could not get sharepoint site data: {e}") from e

        data = response.json()

        # Check for the next page
        if ODATA_NEXT_LINK in data:
            return data[ODATA_VALUE] + recurs_get(data[ODATA_NEXT_LINK], headers)

        return data[ODATA_VALUE]

    result = recurs_get(
        os.environ["GRAPH_BASE_URL"],
        headers=_get_graph_headers(),
    )
    return result
