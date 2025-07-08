import logging
import os

import requests
from grafap._auth import Decorators
from grafap._helpers import _basic_retry

logger = logging.getLogger(__name__)


@Decorators._refresh_graph_token
def get_sp_sites() -> dict:
    """
    Gets all site data in a given tenant
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    @_basic_retry
    def recurs_get(url, headers):
        """
        Recursive function to handle pagination
        """
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error {e.response.status_code}, could not get sharepoint site data: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not get sharepoint site data: {e}"
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Error, could not connect to sharepoint site data: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not get sharepoint site data: {e}")
            raise Exception(f"Error, could not get sharepoint site data: {e}")

        data = response.json()

        # Check for the next page
        if "@odata.nextLink" in data:
            return data["value"] + recurs_get(data["@odata.nextLink"], headers)
        else:
            return data["value"]

    result = recurs_get(
        os.environ["GRAPH_BASE_URL"],
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
    )
    return result
