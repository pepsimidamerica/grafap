"""
This module contains functions for interacting with users in MS Graph, both
actual users and also the site-specific users that are stored in a hidden
sharepoint list.
"""

import logging
import os
from typing import Optional

import requests
from grafap._auth import Decorators
from grafap._helpers import _basic_retry

logger = logging.getLogger(__name__)


@Decorators._refresh_graph_token
def get_ad_users(
    select: str | None = None, filter: str | None = None, expand: str | None = None
) -> dict:
    """
    Gets AD users in a given tenant

    :param select: OData $select query option
    :param filter: OData $filter query option
    :param expand: OData $expand query option
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
                f"Error {e.response.status_code}, could not get user data: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not get user data: {e}"
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Error, could not connect to user data: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not get user data: {e}")
            raise Exception(f"Error, could not get user data: {e}")

        data = response.json()

        # Check for the next page
        if "@odata.nextLink" in data:
            return data["value"] + recurs_get(data["@odata.nextLink"], headers)
        else:
            return data["value"]

    # Construct the query string
    query_params = []
    if select:
        query_params.append(f"$select={select}")
    if filter:
        query_params.append(f"$filter={filter}")
    if expand:
        query_params.append(f"$expand={expand}")

    query_string = "&".join(query_params)
    base_url = "https://graph.microsoft.com/v1.0/users"
    url = f"{base_url}?{query_string}" if query_string else base_url

    result = recurs_get(
        url,
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
    )

    return result


@Decorators._refresh_graph_token
def get_all_sp_users_info(site_id: str) -> dict:
    """
    Query the hidden sharepoint list that contains user information
    Can use "root" as the site_id for the root site, otherwise use the site id
    You would want to use whichever site ID is associated with the list you are querying

    :param site_id: The site id to get user information from
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    @_basic_retry
    def recurs_get(url, headers, params=None):
        """
        Recursive function to handle pagination
        """
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                params=params,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Error, could not connect to sharepoint list data: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not get sharepoint list data: {e}")
            raise Exception(f"Error, could not get sharepoint list data: {e}")

        data = response.json()

        # Check for the next page
        if "@odata.nextLink" in data:
            return data["value"] + recurs_get(data["@odata.nextLink"], headers)
        else:
            return data["value"]

    url = (
        os.environ["GRAPH_BASE_URL"] + site_id + "/lists('User Information List')/items"
    )

    result = recurs_get(
        url,
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
        params={"expand": "fields(select=Id,Email)"},
    )

    return result


@_basic_retry
@Decorators._refresh_graph_token
def get_sp_user_info(
    site_id: str, user_id: Optional[str], email: Optional[str]
) -> dict:
    """
    Get a specific user from the hidden sharepoint list that contains user information

    :param site_id: The site id to get user information from
    :param user_id: The user id to get information for
    :param email: The email to get information for
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    url = (
        os.environ["GRAPH_BASE_URL"] + site_id + "/lists('User Information List')/items"
    )

    if user_id:
        url += "/" + user_id
    elif email:
        url += "?$filter=fields/UserName eq '" + email + "'"

    try:
        response = requests.get(
            url,
            headers={
                "Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"],
                "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly",
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
        )
        raise Exception(
            f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to sharepoint list data: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not get sharepoint list data: {e}")
        raise Exception(f"Error, could not get sharepoint list data: {e}")

    if "value" in response.json():
        if len(response.json()["value"]) == 0:
            raise Exception("Error, could not find user in sharepoint list")
        else:
            return response.json()["value"][0]
    return response.json()


# Doesn't seem to be needed, commenting out for now
# @Decorators.refresh_sp_token
# def get_site_user_by_id(site_url: str, user_id: str) -> dict:
#     """
#     Gets a sharepoint site user by the lookup id
#     """
#     headers = {
#         "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
#         "Accept": "application/json;odata=verbose",
#     }

#     url = f"{site_url}/_api/web/siteusers/getbyid({user_id})"

#     response = requests.get(url, headers=headers, timeout=30)

#     if response.status_code != 200:
#         raise Exception("Error, could not get site user data: " + str(response.content))


@Decorators._refresh_sp_token
def ensure_sp_user(site_url: str, logon_name: str) -> dict:
    """
    Users sharepoint REST API, not MS Graph API. Endpoint is only available
    in the Sharepoint one. Ensure a user exists in given website. This is used
    so that the user can be used in sharepoint lists in that site. If the user has
    never interacted with the site or been picked in a People field, they are not
    available in the Graph API to pick from.

    :param site_url: The site url
    :param logon_name: The user's logon name, i.e. email address
    """
    # Ensure the required environment variable is set
    if "SP_BEARER_TOKEN" not in os.environ:
        raise Exception("Error, could not find SP_BEARER_TOKEN in env")

    # Construct the URL for the ensure user endpoint
    url = f"{site_url}/_api/web/ensureuser"

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
                "Accept": "application/json;odata=verbose;charset=utf-8",
                "Content-Type": "application/json;odata=verbose;charset=utf-8",
            },
            json={"logonName": logon_name},
            timeout=30,
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error {e.response.status_code}, could not ensure user: {e}")
        raise Exception(f"Error {e.response.status_code}, could not ensure user: {e}")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to ensure user: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not ensure user: {e}")
        raise Exception(f"Error, could not ensure user: {e}")

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
