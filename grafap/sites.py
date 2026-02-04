"""
The sites module provides functions for getting data on the high-level sharepoint
site structure of a given tenant. Needed to retrieve a given site ID for
lower-level operations.
"""

import logging
import os

from grafap._auth import Decorators
from grafap._helpers import _check_env, _get_graph_headers, _get_paginated

logger = logging.getLogger(__name__)


@Decorators._refresh_graph_token
def sites_return() -> list[dict]:
    """
    Gets all site data in a given tenant.
    """
    _check_env("GRAPH_BASE_URL")

    url = os.environ["GRAPH_BASE_URL"]

    return _get_paginated(url, headers=_get_graph_headers())
