"""
The users module contains functions for interacting with users in MS Graph, both
actual AD users and also the site-specific users that are stored in a hidden
sharepoint list.
"""

import logging
import os

import requests
from grafap._auth import Decorators
from grafap._constants import (
    DEFAULT_TIMEOUT,
    GRAPH_PREFER_OPTIONAL,
    ODATA_NEXT_LINK,
    ODATA_VALUE,
    USER_INFO_LIST_NAME,
)
from grafap._helpers import (
    _basic_retry,
    _check_env,
    _get_graph_headers,
    _get_paginated,
    _get_sp_headers,
    _make_request,
)

logger = logging.getLogger(__name__)


@Decorators._refresh_graph_token
def ad_users_return(
    select: str | None = None, filter: str | None = None, expand: str | None = None
) -> dict:
    """
    Gets AD users in a given tenant.

    :param select: OData $select query option
    :type select: str | None
    :param filter: OData $filter query option
    :type filter: str | None
    :param expand: OData $expand query option
    :type expand: str | None
    :return: A dictionary containing user information
    :rtype: dict
    """
    _check_env("GRAPH_BASE_URL")

    params = {}

    if select:
        params["$select"] = select
    if filter:
        params["$filter"] = filter
    if expand:
        params["$expand"] = expand

    url = "https://graph.microsoft.com/v1.0/users"

    response = _make_request(
        method="GET",
        url=url,
        headers=_get_graph_headers(),
        context="getting AD users",
        params=params,
    )

    return response.json()


@Decorators._refresh_graph_token
def sp_users_info_return(site_id: str) -> list[dict]:
    """
    Query the hidden sharepoint list that contains user information.
    Can use "root" as the site_id for the root site, otherwise use the site id.
    You would want to use whichever site ID is associated with the list you are querying.

    :param site_id: The site id to get user information from
    :type site_id: str
    :return: A dictionary containing user information
    :rtype: dict
    """
    _check_env("GRAPH_BASE_URL")

    url = (
        f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists('{USER_INFO_LIST_NAME}')/items"
    )

    result = _get_paginated(
        url,
        headers=_get_graph_headers(),
        params={"expand": "fields(select=Id,Email)"},
    )

    return result


@_basic_retry
@Decorators._refresh_graph_token
def sp_user_info_return(
    site_id: str, user_id: str | None = None, email: str | None = None
) -> dict:
    """
    Get a specific user from the hidden sharepoint list that contains user information.

    :param site_id: The site id to get user information from
    :type site_id: str
    :param user_id: The user id to get information for
    :type user_id: str | None
    :param email: The email to get information for
    :type email: str | None
    :return: A dictionary containing user information
    :rtype: dict
    """
    _check_env("GRAPH_BASE_URL")

    url = (
        f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists('{USER_INFO_LIST_NAME}')/items"
    )

    if user_id:
        url += "/" + user_id
    elif email:
        url += "?$filter=fields/UserName eq '" + email + "'"

    try:
        response = requests.get(
            url,
            headers=_get_graph_headers({"Prefer": GRAPH_PREFER_OPTIONAL}),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
        )
        raise Exception(
            f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
        ) from e
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to sharepoint list data: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not get sharepoint list data: {e}")
        raise Exception(f"Error, could not get sharepoint list data: {e}") from e

    if ODATA_VALUE in response.json():
        if len(response.json()[ODATA_VALUE]) == 0:
            raise Exception("Error, could not find user in sharepoint list")

        return response.json()[ODATA_VALUE][0]
    return response.json()


@Decorators._refresh_sp_token
def sp_user_ensure(site_url: str, logon_name: str) -> dict:
    """
    Users sharepoint REST API, not MS Graph API. Endpoint is only available
    in the Sharepoint one. Ensure a user exists in given website. This is used
    so that the user can be used in sharepoint lists in that site. If the user has
    never interacted with the site or been picked in a People field, they are not
    available in the Graph API to pick from.

    :param site_url: The site url
    :param logon_name: The user's logon name, i.e. email address
    """
    # Construct the URL for the ensure user endpoint
    url = f"{site_url}/_api/web/ensureuser"

    try:
        response = requests.post(
            url,
            headers=_get_sp_headers(),
            json={"logonName": logon_name},
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error {e.response.status_code}, could not ensure user: {e}")
        raise Exception(
            f"Error {e.response.status_code}, could not ensure user: {e}"
        ) from e
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to ensure user: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not ensure user: {e}")
        raise Exception(f"Error, could not ensure user: {e}") from e

    # Check for errors in the response
    if response.status_code != 200:
        logger.error(
            f"Error {response.status_code}, could not ensure user: {response.content}"
        )
        raise Exception(
            f"Error {response.status_code}, could not ensure user: {response.content}"
        )

    # Return the JSON response
    return response.json()
