"""
The lists module deals with interacting with sharepoint lists and attachments
on these lists. It provides standard functions for getting, creating, updating,
and deleting item data.
"""

import logging
import os
from typing import Any

import requests
from grafap._auth import Decorators
from grafap._helpers import _basic_retry

logger = logging.getLogger(__name__)


@Decorators._refresh_graph_token
def lists_return(site_id: str) -> dict:
    """
    Gets all lists in a given site.

    :param site_id: The site id to get lists from
    :type site_id: str
    :return: A dictionary of lists in the site
    :rtype: dict
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists"

    @_basic_retry
    def recurs_get(url, headers):
        """
        Recursive function to handle pagination.
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
            ) from e
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Error, could not connect to sharepoint: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not get sharepoint list data: {e}")
            raise Exception(f"Error, could not get sharepoint list data: {e}") from e

        data = response.json()

        # Check for the next page
        if "@odata.nextLink" in data:
            return data["value"] + recurs_get(data["@odata.nextLink"], headers)

        return data["value"]

    result = recurs_get(
        url=url,
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
    )

    return result


@Decorators._refresh_graph_token
def list_items_return(
    site_id: str,
    list_id: str,
    filter_query: str | None = None,
    select_query: str | None = None,
) -> dict:
    """
    Gets field data from a sharepoint list.

    Note: If you're using the filter_query expression, whichever field you
    want to filter on needs to be indexed or you'll get an error.
    To index a column, just add it in the sharepoint list settings.

    :param site_id: The site id to get lists from
    :type site_id: str
    :param list_id: The list id to get items from
    :type list_id: str
    :param filter_query: An optional OData filter query
    :type filter_query: str | None
    :param select_query: An optional OData select query to limit fields returned
    :type select_query: str | None
    :return: A dictionary of list items with field data
    :rtype: dict
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items"

    @_basic_retry
    def recurs_get(url, headers):
        """
        Recursive function to handle pagination.
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
            ) from e
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Error, could not connect to sharepoint: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not get sharepoint list data: {e}")
            raise Exception(f"Error, could not get sharepoint list data: {e}") from e

        data = response.json()

        # Check for the next page
        if "@odata.nextLink" in data:
            return data["value"] + recurs_get(data["@odata.nextLink"], headers)

        return data["value"]

    if select_query:
        url += f"?expand=fields($select={select_query})"
    else:
        url += "?expand=fields"

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
def list_item_return(site_id: str, list_id: str, item_id: str) -> dict:
    """
    Gets field data from a specific sharepoint list item.

    :param site_id: The site id to get lists from
    :type site_id: str
    :param list_id: The list id to get items from
    :type list_id: str
    :param item_id: The id of the list item to get field data from
    :type item_id: str
    :return: A dictionary of list item field data
    :rtype: dict
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items/{item_id}"

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
        ) from e
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to sharepoint: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not get sharepoint list data: {e}")
        raise Exception(f"Error, could not get sharepoint list data: {e}") from e

    return response.json()


@Decorators._refresh_graph_token
def list_item_create(site_id: str, list_id: str, field_data: dict) -> dict:
    """
    Create a new item in SharePoint.

    :param site_id: The site id to create the item in
    :type site_id: str
    :param list_id: The list id to create the item in
    :type list_id: str
    :param field_data: A dictionary of field data to create the item with, recommended
                        to pull a list of fields from the list first to get the correct field names
    :type field_data: dict
    :return: A dictionary of the created list item
    :rtype: dict
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items"

    try:
        response = requests.post(
            url=url,
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
        ) from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not create item in sharepoint: {e}")
        raise Exception(f"Error, could not create item in sharepoint: {e}")

    return response.json()


@_basic_retry
@Decorators._refresh_graph_token
def list_item_delete(site_id: str, list_id: str, item_id: str) -> None:
    """
    Delete an item in SharePoint.

    :param site_id: The site id to delete the item from
    :type site_id: str
    :param list_id: The list id to delete the item from
    :type list_id: str
    :param item_id: The id of the list item to delete
    :type item_id: str
    :return: None
    :rtype: None
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items/{item_id}"

    try:
        response = requests.delete(
            url=url,
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
        ) from e
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to sharepoint: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not delete item in sharepoint: {e}")
        raise Exception(f"Error, could not delete item in sharepoint: {e}") from e


@_basic_retry
@Decorators._refresh_graph_token
def list_item_update(
    site_id: str, list_id: str, item_id: str, field_data: dict[str, Any]
) -> None:
    """
    Update an item in SharePoint.

    :param site_id: The site id to update the item in
    :type site_id: str
    :param list_id: The list id to update the item in
    :type list_id: str
    :param item_id: The id of the list item to update
    :type item_id: str
    :param field_data: A dictionary of field data to update the item with, only include fields you're updating. Recommended to pull a list of fields from the list first to get the correct field names
    :type field_data: dict[str, Any]
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items/{item_id}/fields"

    try:
        response = requests.patch(
            url=url,
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
        ) from e
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Error, could not connect to sharepoint: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not update item in sharepoint: {e}")
        raise Exception(f"Error, could not update item in sharepoint: {e}") from e


@Decorators._refresh_sp_token
def list_item_attachments_return(
    site_url: str, list_name: str, item_id: int, download: bool = False
) -> list[dict]:
    """
    Gets attachments for a sharepoint list item. Returns as a list of
    dicts (if the given list item does have attachments) if download is False.
    In other words, just downloading info about the attachments.

    Note: Uses the Sharepoint REST API, and not the Graph API.

    :param site_url: The site url to get list attachments from
    :type site_url: str
    :param item_id: The id of the list item to get attachments from
    :type item_id: int
    :param download: If True, download the attachments to the local filesystem
    :type download: bool
    :return: A list of dictionaries containing attachment info or data
    :rtype: list[dict]
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
        ) from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not get list attachments: {e}")
        raise Exception(f"Error, could not get list attachments: {e}") from e

    # Get the attachment data
    data = response.json().get("d", {})
    attachments = data.get("AttachmentFiles", {}).get("results", [])

    if not download:
        return [
            {"name": str(x.get("FileName")), "url": str(x.get("ServerRelativeUrl"))}
            for x in attachments
        ]

    @_basic_retry
    def download_attachment(attachment: dict) -> dict:
        """
        Helper function to download an attachment.
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
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not download attachment: {e}")
            raise Exception(f"Error, could not download attachment: {e}") from e

        return {
            "name": attachment.get("FileName"),
            "url": attachment.get("ServerRelativeUrl"),
            "data": attachment_response.content,
        }

    downloaded_files = [download_attachment(x) for x in attachments]

    return downloaded_files
