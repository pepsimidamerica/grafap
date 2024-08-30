import os

import requests

from grafap.auth import Decorators


@Decorators.refresh_graph_token
def get_sp_lists(site_id: str) -> dict:
    """
    Gets all lists in a given site

    :param site_id: The site id to get lists from
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

    Note: If you're using the filter_query expression, whichever field you
    want to filter on needs to be indexed or you'll get an error.
    To index a column, just add it in the sharepoint list settings.

    :param site_id: The site id to get lists from
    :param list_id: The list id to get items from
    :param filter_query: An optional OData filter query
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

    :param site_id: The site id to get lists from
    :param list_id: The list id to get items from
    :param item_id: The id of the list item to get field data from
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

    :param site_id: The site id to create the item in
    :param list_id: The list id to create the item in
    :param field_data: A dictionary of field data to create the item with, recommended to pull a list of fields from the list first to get the correct field names
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

    :param site_id: The site id to delete the item from
    :param list_id: The list id to delete the item from
    :param item_id: The id of the list item to delete
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

    :param site_id: The site id to update the item in
    :param list_id: The list id to update the item in
    :param item_id: The id of the list item to update
    :param field_data: A dictionary of field data to update the item with, only include fields you're updating. Recommended to pull a list of fields from the list first to get the correct field names
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
