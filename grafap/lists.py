"""
The lists module deals with interacting with sharepoint lists and attachments
on these lists. It provides standard functions for getting, creating, updating,
and deleting item data.
"""

import logging
import os
from typing import Any, Dict
from urllib.parse import urlparse

import requests
from grafap._auth import Decorators
from grafap._helpers import _basic_retry

logger = logging.getLogger(__name__)


@Decorators._refresh_graph_token
def get_sp_lists(site_id: str) -> dict:
    """
    Gets all lists in a given site

    :param site_id: The site id to get lists from
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
                f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Error, could not connect to sharepoint: {e}")
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

    result = recurs_get(
        os.environ["GRAPH_BASE_URL"] + site_id + "/lists",
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
    )

    return result


@Decorators._refresh_graph_token
def get_sp_list_items(
    site_id: str, list_id: str, filter_query: str | None = None
) -> dict:
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
                f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not get sharepoint list data: {e}"
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Error, could not connect to sharepoint: {e}")
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


@_basic_retry
@Decorators._refresh_graph_token
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
        logger.error(f"Error, could not connect to sharepoint: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not get sharepoint list data: {e}")
        raise Exception(f"Error, could not get sharepoint list data: {e}")

    return response.json()


@Decorators._refresh_graph_token
def create_sp_item(site_id: str, list_id: str, field_data: dict) -> dict:
    """
    Create a new item in SharePoint

    :param site_id: The site id to create the item in
    :param list_id: The list id to create the item in
    :param field_data: A dictionary of field data to create the item with, recommended
    to pull a list of fields from the list first to get the correct field names
    """
    try:
        response = requests.post(
            os.environ["GRAPH_BASE_URL"] + site_id + "/lists/" + list_id + "/items",
            headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
            json={"fields": field_data},
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"Error {e.response.status_code}, could not create item in sharepoint: {e}"
        )
        raise Exception(
            f"Error {e.response.status_code}, could not create item in sharepoint: {e}"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not create item in sharepoint: {e}")
        raise Exception(f"Error, could not create item in sharepoint: {e}")

    return response.json()


@_basic_retry
@Decorators._refresh_graph_token
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
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"Error {e.response.status_code}, could not delete item in sharepoint: {e}"
        )
        raise Exception(
            f"Error {e.response.status_code}, could not delete item in sharepoint: {e}"
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to sharepoint: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not delete item in sharepoint: {e}")
        raise Exception(f"Error, could not delete item in sharepoint: {e}")


@_basic_retry
@Decorators._refresh_graph_token
def update_sp_item(
    site_id: str, list_id: str, item_id: str, field_data: Dict[str, Any]
):
    """
    Update an item in SharePoint

    :param site_id: The site id to update the item in
    :param list_id: The list id to update the item in
    :param item_id: The id of the list item to update
    :param field_data: A dictionary of field data to update the item with, only
    include fields you're updating. Recommended to pull a list of fields from the list first to get the correct field names
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
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"Error {e.response.status_code}, could not update item in sharepoint: {e}"
        )
        raise Exception(
            f"Error {e.response.status_code}, could not update item in sharepoint: {e}"
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to sharepoint: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not update item in sharepoint: {e}")
        raise Exception(f"Error, could not update item in sharepoint: {e}")


@Decorators._refresh_sp_token
def get_list_attachments(
    site_url: str, list_name: str, item_id: int, download: bool = False
) -> list[dict]:
    """
    Gets attachments for a sharepoint list item. Returns as a list of
    dicts (if the given list item does have attachments) if download is False.
    In other words, just downloading info about the attachments.

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

    try:
        response = requests.get(
            url,
            headers={
                "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
                "Accept": "application/json;odata=verbose;charset=utf-8",
                "Content-Type": "application/json;odata=verbose;charset=utf-8",
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"Error {e.response.status_code}, could not get list attachments: {e}"
        )
        raise Exception(
            f"Error {e.response.status_code}, could not get list attachments: {e}"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not get list attachments: {e}")
        raise Exception(f"Error, could not get list attachments: {e}")

    # Get the attachment data
    data = response.json().get("d", {})
    attachments = data.get("AttachmentFiles", {}).get("results", [])

    if not download:
        return [
            {"name": str(x.get("FileName")), "url": str(x.get("ServerRelativeUrl"))}
            for x in attachments
        ]

    @_basic_retry
    def download_attachment(attachment):
        """
        Helper function to download an attachment
        """
        relative_url = attachment.get("ServerRelativeUrl")
        try:
            attachment_response = requests.get(
                f"{site_url}/_api/Web/GetFileByServerRelativeUrl('{relative_url}')/$value",
                headers={
                    "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
                    "Accept": "application/json;odata=verbose;charset=utf-8",
                    "Content-Type": "application/json;odata=verbose;charset=utf-8",
                },
                timeout=30,
            )
            attachment_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error {e.response.status_code}, could not download attachment: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not download attachment: {e}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not download attachment: {e}")
            raise Exception(f"Error, could not download attachment: {e}")

        return {
            "name": attachment.get("FileName"),
            "url": attachment.get("ServerRelativeUrl"),
            "data": attachment_response.content,
        }

    downloaded_files = []
    for attachment in attachments:
        downloaded_files.append(download_attachment(attachment))

    return downloaded_files


@Decorators._refresh_sp_token
def get_file(file_url: str) -> dict:
    """
    Downloads a file from a SharePoint site, likely stored in a document library.

    :param file_url: The direct URL to the file in the SharePoint document library
    :return: A dictionary containing the file name, URL, and file content
    """
    if "SP_BEARER_TOKEN" not in os.environ:
        raise Exception("Error, could not find SP_BEARER_TOKEN in env")

    headers = {
        "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
        "Accept": "application/json;odata=verbose;charset=utf-8",
        "Content-Type": "application/json;odata=verbose;charset=utf-8",
    }

    # Parse the file URL to get the site URL and relative URL
    parsed_url = urlparse(file_url)
    path_parts = parsed_url.path.split("/")
    site_path = "/".join(path_parts[:3])  # This will include the site path
    relative_url = "/".join(path_parts[3:])  # This will include the rest of the path

    site_url = f"{parsed_url.scheme}://{parsed_url.netloc}{site_path}"

    try:
        response = requests.get(
            f"{site_url}/_api/Web/GetFileByUrl(@url)/$value?@url='{file_url}'",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error {e.response.status_code}, could not download file: {e}")
        raise Exception(f"Error {e.response.status_code}, could not download file: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not download file: {e}")
        raise Exception(f"Error, could not download file: {e}")

    file_name = relative_url.split("/")[-1]

    return {"name": file_name, "url": file_url, "data": response.content}


@Decorators._refresh_sp_token
def delete_file(file_url: str):
    """
    Deletes a file from a SharePoint site, likley stored in a document library.

    :param file_url: The direct URL to the file in the SharePoint document library
    """
    if "SP_BEARER_TOKEN" not in os.environ:
        raise Exception("Error, could not find SP_BEARER_TOKEN in env")

    headers = {
        "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
        "Accept": "application/json;odata=verbose;charset=utf-8",
        "Content-Type": "application/json;odata=verbose;charset=utf-8",
    }

    # Parse the file URL to get the site URL and relative URL
    parsed_url = urlparse(file_url)
    path_parts = parsed_url.path.split("/")
    site_path = "/".join(path_parts[:3])
    relative_url = "/".join(path_parts[3:])  # This will include the rest of the path

    site_url = f"{parsed_url.scheme}://{parsed_url.netloc}{site_path}"

    try:
        response = requests.delete(
            # f"{site_url}/_api/Web/GetFileByServerRelativeUrl('{relative_url}')",
            f"{site_url}/_api/Web/GetFileByUrl(@url)?@url='{file_url}'",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error {e.response.status_code}, could not delete file: {e}")
        raise Exception(f"Error {e.response.status_code}, could not delete file: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not delete file: {e}")
        raise Exception(f"Error, could not delete file: {e}")

    return None
