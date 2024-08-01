"""
This module contains functions to interact with Microsoft Graph API
"""

import json
import os
import re
from datetime import datetime, timedelta
from pprint import pprint
from typing import Optional
from urllib import response

import requests


class Decorators:
    """
    Decorators class for handling token refreshing
    for Microsoft Graph and Sharepoint Rest API
    """

    @staticmethod
    def refresh_graph_token(decorated):
        """
        Decorator to refresh the graph access token if it has expired
        """

        def wrapper(*args, **kwargs):
            """
            Wrapper function
            """
            if "GRAPH_BEARER_TOKEN_EXPIRES_AT" not in os.environ:
                expires_at = "01/01/1901 00:00:00"
            else:
                expires_at = os.environ["GRAPH_BEARER_TOKEN_EXPIRES_AT"]
            if (
                "GRAPH_BEARER_TOKEN" not in os.environ
                or datetime.strptime(expires_at, "%m/%d/%Y %H:%M:%S") < datetime.now()
            ):
                Decorators.get_graph_token()
            return decorated(*args, **kwargs)

        wrapper.__name__ = decorated.__name__
        return wrapper

        # @staticmethod
        # def refresh_sp_token(decorated):
        # """
        # Decorator to refresh the sharepoint rest API access token if it has expired
        # """

        # def wrapper(*args, **kwargs):
        #     """
        #     Wrapper function
        #     """
        #     if "SP_BEARER_TOKEN_EXPIRES_AT" not in os.environ:
        #         expires_at = "01/01/1901 00:00:00"
        #     else:
        #         expires_at = os.environ["SP_BEARER_TOKEN_EXPIRES_AT"]
        #     if (
        #         "SP_BEARER_TOKEN" not in os.environ
        #         or datetime.strptime(expires_at, "%m/%d/%Y %H:%M:%S") < datetime.now()
        #     ):
        #         Decorators.get_sp_token()
        #     return decorated(*args, **kwargs)

        # wrapper.__name__ = decorated.__name__
        # return wrapper

    @staticmethod
    def get_graph_token():
        """
        Get Microsoft Graph bearer token
        """
        if "GRAPH_LOGIN_BASE_URL" not in os.environ:
            raise Exception("Error, could not find GRAPH_LOGIN_BASE_URL in env")
        if "GRAPH_TENANT_ID" not in os.environ:
            raise Exception("Error, could not find GRAPH_TENANT_ID in env")
        if "GRAPH_CLIENT_ID" not in os.environ:
            raise Exception("Error, could not find GRAPH_CLIENT_ID in env")
        if "GRAPH_CLIENT_SECRET" not in os.environ:
            raise Exception("Error, could not find GRAPH_CLIENT_SECRET in env")
        if "GRAPH_GRANT_TYPE" not in os.environ:
            raise Exception("Error, could not find GRAPH_GRANT_TYPE in env")
        if "GRAPH_SCOPES" not in os.environ:
            raise Exception("Error, could not find GRAPH_SCOPES in env")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(
            os.environ["GRAPH_LOGIN_BASE_URL"]
            + os.environ["GRAPH_TENANT_ID"]
            + "/oauth2/v2.0/token",
            headers=headers,
            data={
                "client_id": os.environ["GRAPH_CLIENT_ID"],
                "client_secret": os.environ["GRAPH_CLIENT_SECRET"],
                "grant_type": os.environ["GRAPH_GRANT_TYPE"],
                "scope": os.environ["GRAPH_SCOPES"],
            },
            timeout=30,
        )
        try:
            os.environ["GRAPH_BEARER_TOKEN"] = response.json()["access_token"]
        except Exception as e:
            raise Exception(
                "Error, could not set OS env bearer token: " + str(response.content)
            )
        try:
            expires_at = datetime.now() + timedelta(
                seconds=response.json()["expires_in"]
            )
            os.environ["GRAPH_BEARER_TOKEN_EXPIRES_AT"] = expires_at.strftime(
                "%m/%d/%Y %H:%M:%S"
            )
        except Exception as e:
            print("Error, could not set os env expires at: ", e)
            raise Exception("Error, could not set os env expires at: " + str(e))

        # @staticmethod
        # def get_sp_token():
        # """
        # Gets Sharepoint Rest API bearer token.
        # """
        # if "SP_LOGIN_BASE_URL" not in os.environ:
        #     raise Exception("Error, could not find SP_LOGIN_BASE_URL in env")
        # if "SP_TENANT_ID" not in os.environ:
        #     raise Exception("Error, could not find SP_TENANT_ID in env")
        # if "SP_CLIENT_ID" not in os.environ:
        #     raise Exception("Error, could not find SP_CLIENT_ID in env")
        # if "SP_CLIENT_SECRET" not in os.environ:
        #     raise Exception("Error, could not find SP_CLIENT_SECRET in env")
        # if "SP_GRANT_TYPE" not in os.environ:
        #     raise Exception("Error, could not find SP_GRANT_TYPE in env")
        # if "SP_SITE" not in os.environ:
        #     raise Exception("Error, could not find SP_SITE in env")

        # headers = {
        #     "Accept": "application/json",
        #     "Content-Type": "application/x-www-form-urlencoded",
        # }

        # response = requests.post(
        #     os.environ["SP_LOGIN_BASE_URL"]
        #     + os.environ["SP_TENANT_ID"]
        #     + "/oauth2/token",
        #     headers=headers,
        #     data={
        #         "client_id": os.environ["SP_CLIENT_ID"],
        #         "client_secret": os.environ["SP_CLIENT_SECRET"],
        #         "grant_type": os.environ["SP_GRANT_TYPE"],
        #         "resource": os.environ["SP_SITE"],
        #     },
        #     timeout=30,
        # )

        # try:
        #     os.environ["SP_BEARER_TOKEN"] = response.json()["access_token"]
        # except Exception as e:
        #     print("Error, could not set OS env bearer token: ", e)
        #     print(response.content)
        #     raise Exception("Error, could not set OS env bearer token: " + str(e))
        # try:
        #     expires_at = datetime.now() + timedelta(
        #         seconds=float(response.json()["expires_in"])
        #     )
        #     os.environ["SP_BEARER_TOKEN_EXPIRES_AT"] = expires_at.strftime(
        #         "%m/%d/%Y %H:%M:%S"
        #     )
        # except Exception as e:
        #     print("Error, could not set os env expires at: ", e)
        #     raise Exception("Error, could not set os env expires at: " + str(e))

        # print(os.environ["SP_BEARER_TOKEN"])


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
def get_sp_sites() -> dict:
    """
    Gets all site data in a given tenant
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
                f"Error {response.status_code}, could not get sharepoint site data: ",
                response.content,
            )
            raise Exception(
                f"Error {response.status_code}, could not get sharepoint site data: "
                + str(response.content)
            )

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


@Decorators.refresh_graph_token
def get_sp_lists(site_id: str) -> dict:
    """
    Gets all lists in a given site
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

    result = recurs_get(
        os.environ["GRAPH_BASE_URL"] + site_id + "/lists",
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
    )

    return result


@Decorators.refresh_graph_token
def get_sp_list_items(site_id: str, list_id: str, filter_query: str = None) -> dict:
    """
    Gets field data from a sharepoint list
    filter_query is an optional OData filter query
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
        os.environ["GRAPH_BASE_URL"]
        + site_id
        + "/lists/"
        + list_id
        + "/items?expand=fields"
    )

    if filter_query:
        url += "&$filter=" + filter_query

    result = recurs_get(
        url,
        headers={
            "Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"],
            "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly",
        },
    )

    return result


@Decorators.refresh_graph_token
def get_sp_list_item(site_id: str, list_id: str, item_id: str) -> dict:
    """
    Gets field data from a specific sharepoint list item
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    url = (
        os.environ["GRAPH_BASE_URL"]
        + site_id
        + "/lists/"
        + list_id
        + "/items/"
        + item_id
    )

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

    return response.json()


@Decorators.refresh_graph_token
def create_sp_item(site_id: str, list_id: str, field_data: dict) -> dict:
    """
    Create a new item in SharePoint
    """
    try:
        response = requests.post(
            os.environ["GRAPH_BASE_URL"] + site_id + "/lists/" + list_id + "/items",
            headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
            json={"fields": field_data},
            timeout=30,
        )
        if response.status_code != 201:
            print(
                f"Error {response.status_code}, could not create item in sharepoint: ",
                response.content,
            )
            raise Exception(
                f"Error {response.status_code}, could not create item in sharepoint: "
                + str(response.content)
            )
    except Exception as e:
        print("Error, could not create item in sharepoint: ", e)
        raise Exception("Error, could not create item in sharepoint: " + str(e))

    return response.json()


@Decorators.refresh_graph_token
def delete_sp_item(site_id: str, list_id: str, item_id: str):
    """
    Delete an item in SharePoint
    """
    try:
        response = requests.delete(
            os.environ["GRAPH_BASE_URL"]
            + site_id
            + "/lists/"
            + list_id
            + "/items/"
            + item_id,
            headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
            timeout=30,
        )
        if response.status_code != 204:
            print(
                f"Error {response.status_code}, could not delete item in sharepoint: ",
                response.content,
            )
            raise Exception(
                f"Error {response.status_code}, could not delete item in sharepoint: "
                + str(response.content)
            )
    except Exception as e:
        print("Error, could not delete item in sharepoint: ", e)
        raise Exception("Error, could not delete item in sharepoint: " + str(e))


@Decorators.refresh_graph_token
def update_sp_item(
    site_id: str, list_id: str, item_id: str, field_data: dict[str, str]
):
    """
    Update an item in SharePoint
    """
    try:
        response = requests.patch(
            os.environ["GRAPH_BASE_URL"]
            + site_id
            + "/lists/"
            + list_id
            + "/items/"
            + item_id
            + "/fields",
            headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
            json=field_data,
            timeout=30,
        )
        if response.status_code != 200:
            print(
                f"Error {response.status_code}, could not update item in sharepoint: ",
                response.content,
            )
            raise Exception(
                f"Error {response.status_code}, could not update item in sharepoint: "
                + str(response.content)
            )
    except Exception as e:
        print("Error, could not update item in sharepoint: ", e)
        raise Exception("Error, could not update item in sharepoint: " + str(e))


@Decorators.refresh_graph_token
def get_sp_termstore_groups(site_id: str) -> dict:
    """
    Lists all termstore group objects in a site
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    response = requests.get(
        os.environ["GRAPH_BASE_URL"] + site_id + "/termStore/groups",
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
        timeout=30,
    )

    if response.status_code != 200:
        print(
            f"Error {response.status_code}, could not get termstore groups: ",
            response.content,
        )
        raise Exception(
            f"Error {response.status_code}, could not get termstore groups: "
            + str(response.content)
        )

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


# # @Decorators.refresh_graph_token_delegated
# def get_user_notebooks():
#     """
#     Gets all notebooks for the signed-in user
#     """
#     if "GRAPH_BASE_URL" not in os.environ:
#         raise Exception("Error, could not find GRAPH_BASE_URL in env")

#     response = requests.get(
#         os.environ["GRAPH_BASE_URL"] + "me/onenote/notebooks",
#         headers={
#             "Authorization": "Bearer " + os.environ["USER_BEARER_TOKEN"],
#             "Accept": "application/json",
#         },
#         timeout=30,
#     )

#     if response.status_code != 200:
#         print("Error, could not get user notebooks: ", response.content)
#         raise Exception("Error, could not get user notebooks: " + str(response.content))

#     return response.json()


# # @Decorators.refresh_graph_token_delegated
# def get_notebook_sections(notebook_id: str):
#     """
#     Gets all sections in a notebook
#     """
#     if "GRAPH_BASE_URL" not in os.environ:
#         raise Exception("Error, could not find GRAPH_BASE_URL in env")

#     response = requests.get(
#         os.environ["GRAPH_BASE_URL"]
#         + "me/onenote/notebooks/"
#         + notebook_id
#         + "/sections",
#         headers={
#             "Authorization": "Bearer " + os.environ["USER_BEARER_TOKEN"],
#             "Accept": "application/json",
#         },
#         timeout=30,
#     )

#     if response.status_code != 200:
#         print("Error, could not get notebook sections: ", response.content)
#         raise Exception(
#             "Error, could not get notebook sections: " + str(response.content)
#         )

#     return response.json()


# # @Decorators.refresh_graph_token_delegated
# def get_section_pages(notebook_id: str, section_id: str):
#     """
#     Gets all pages in a section
#     """
#     if "GRAPH_BASE_URL" not in os.environ:
#         raise Exception("Error, could not find GRAPH_BASE_URL in env")

#     response = requests.get(
#         os.environ["GRAPH_BASE_URL"]
#         + "me/onenote/notebooks/"
#         + notebook_id
#         + "/sections/"
#         + section_id
#         + "/pages",
#         headers={
#             "Authorization": "Bearer " + os.environ["USER_BEARER_TOKEN"],
#             "Accept": "application/json",
#         },
#         timeout=30,
#     )

#     if response.status_code != 200:
#         print("Error, could not get section pages: ", response.content)
#         raise Exception("Error, could not get section pages: " + str(response.content))

#     return response.json()
