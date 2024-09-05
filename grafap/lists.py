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


@Decorators.refresh_sp_token
def get_list_attachments(
    site_url: str, list_name: str, item_id: int, download: bool = False
) -> list[dict]:
    """
    Gets attachments for a sharepoint list item. Returns as a list of
    dicts (if the given list item does have attachments) if download is False.
    In other wirds, just downloading info about the attachments.

    Note: Uses the Sharepoint REST API, and not the Graph API.

    :param site_url: The site url to get list attachments from
    :param item_id: The id of the list item to get attachments from
    :param download: If True, download the attachments to the local filesystem
    """
    # Ensure the required environment variable is set
    if "SP_BEARER_TOKEN" not in os.environ:
        raise Exception("Error, could not find SP_BEARER_TOKEN in env")

    # Construct the URL for the ensure user endpoint
    url = f"{site_url}/_api/lists/getByTitle('{list_name}')/items({item_id})?$select=AttachmentFiles,Title&$expand=AttachmentFiles"

    response = requests.get(
        url,
        headers={
            "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
            "Accept": "application/json;odata=verbose;charset=utf-8",
            "Content-Type": "application/json;odata=verbose;charset=utf-8",
        },
        timeout=30,
    )

    # Check for errors in the response
    if response.status_code != 200:
        print(
            f"Error {response.status_code}, could not get list attachments: ",
            response.content,
        )
        raise Exception(
            f"Error {response.status_code}, could not get list attachments: "
            + str(response.content)
        )

    # Get the attachment data
    data = response.json().get("d", {})
    attachments = data.get("AttachmentFiles", {}).get("results", [])

    pass

    if not download:
        return [
            {"name": str(x.get("FileName")), "url": str(x.get("ServerRelativeUrl"))}
            for x in attachments
        ]

    downloaded_files = []

    for attachment in attachments:

        relative_url = attachment.get("ServerRelativeUrl")
        attachment_response = requests.get(
            f"{site_url}/_api/Web/GetFileByServerRelativeUrl('{relative_url}')/$value",
            headers={
                "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
                "Accept": "application/json;odata=verbose;charset=utf-8",
                "Content-Type": "application/json;odata=verbose;charset=utf-8",
            },
            timeout=30,
        )

        # Check for errors in the response
        if attachment_response.status_code != 200:
            print(
                f"Error {attachment_response.status_code}, could not download attachment: ",
                attachment_response.content,
            )
            raise Exception(
                f"Error {attachment_response.status_code}, could not download attachment: "
                + str(attachment_response.content)
            )

        downloaded_files.append(
            {
                "name": attachment.get("FileName"),
                "url": attachment.get("ServerRelativeUrl"),
                "data": attachment_response.content,
            }
        )

    return downloaded_files
