"""
The termstore module provides function to interact with a sharepoint site's
termstore groups, which are used to manage metadata in sharepoint.
"""

import logging
import os

from grafap._auth import Decorators
from grafap._helpers import _basic_retry, _check_env, _get_graph_headers, _make_request

logger = logging.getLogger(__name__)


@_basic_retry
@Decorators._refresh_graph_token
def termstore_groups_return(site_id: str) -> dict:
    """
    Lists all termstore group objects in a site.

    :param site_id: The site id
    :type site_id: str
    :return: A dictionary containing the termstore groups
    :rtype: dict
    """
    _check_env("GRAPH_BASE_URL")

    response = _make_request(
        method="GET",
        url=os.environ["GRAPH_BASE_URL"] + site_id + "/termStore/groups",
        headers=_get_graph_headers(),
        context="get termstore groups",
    )

    return response.json()
