import os

import requests

from grafap._auth import Decorators
from grafap._helpers import _basic_retry


@_basic_retry
@Decorators._refresh_graph_token
def get_sp_termstore_groups(site_id: str) -> dict:
    """
    Lists all termstore group objects in a site

    :param site_id: The site id
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    try:
        response = requests.get(
            os.environ["GRAPH_BASE_URL"] + site_id + "/termStore/groups",
            headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise Exception(
            f"Error {e.response.status_code}, could not get termstore groups: {e}"
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error, could not get termstore groups: {e}")

    return response.json()
