"""
This module contains functions for interacting with users in MS Graph, both
actual users and also the site-specific users that are stored in a hidden
sharepoint list.
"""

import os
from typing import Optional

import requests

from grafap.auth import Decorators


@Decorators.refresh_graph_token
def get_users() -> dict:
    """
    Gets all users in a given tenant
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    def recurs_get(url, headers):
        """
        Recursive function to handle pagination
        """
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(
                f"Error {response.status_code}, could not get user data: ",
                response.content,
            )
            raise Exception(
                f"Error {response.status_code}, could not get user data: "
                + str(response.content)
            )

        data = response.json()

        # Check for the next page
        if "@odata.nextLink" in data:
            return data["value"] + recurs_get(data["@odata.nextLink"], headers)
        else:
            return data["value"]

    result = recurs_get(
        "https://graph.microsoft.com/v1.0/" + "users",
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
    )

    return result


@Decorators.refresh_graph_token
def get_all_sp_users_info(site_id: str) -> dict:
    """
    Query the hidden sharepoint list that contains user information
    Can use "root" as the site_id for the root site, otherwise use the site id
    You would want to use whichever site ID is associated with the list you are querying
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    def recurs_get(url, headers, params=None):
        """
        Recursive function to handle pagination
        """
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            params=params,
        )

        if response.status_code != 200:
            print(
                f"Error {response.status_code}, could not get sharepoint list data: ",
                response.content,
            )
            raise Exception(
                f"Error {response.status_code}, could not get sharepoint list data: "
                + str(response.content)
            )

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


@Decorators.refresh_graph_token
def get_sp_user_info(
    site_id: str, user_id: Optional[str], email: Optional[str]
) -> dict:
    """
    Get a specific user from the hidden sharepoint list that contains user information
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

    response = requests.get(
        url,
        headers={
            "Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"],
            "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly",
        },
        timeout=30,
    )

    if response.status_code != 200:
        print(
            f"Error {response.status_code}, could not get sharepoint list data: ",
            response.content,
        )
        raise Exception(
            f"Error {response.status_code}, could not get sharepoint list data: "
            + str(response.content)
        )

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
#         print("Status Code: ", response.status_code)
#         print("Error, could not get site user data: ", response.content)
#         raise Exception("Error, could not get site user data: " + str(response.content))
