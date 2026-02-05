"""
The lists module deals with interacting with sharepoint lists and attachments
on these lists. It provides standard functions for getting, creating, updating,
and deleting item data.
"""

import logging
import os
from typing import Any

from grafap._auth import Decorators
from grafap._constants import (
    GRAPH_PREFER_OPTIONAL,
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
def lists_return(site_id: str) -> list[dict]:
    """
    Gets all lists in a given site.

    :param site_id: The site id to get lists from
    :type site_id: str
    :return: A list of dictionaries of sharepoint lists
    :rtype: list[dict]
    """
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists"

    return _get_paginated(
        url,
        headers=_get_graph_headers(),
        context="get sharepoint lists",
    )


@Decorators._refresh_graph_token
def list_items_return(
    site_id: str,
    list_id: str,
    filter_query: str | None = None,
    select_query: str | None = None,
) -> list[dict]:
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
    :return: A list of dictionaries of list item field data
    :rtype: list[dict]
    """
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items"

    params = {"$expand": "fields"}

    if select_query:
        params["$expand"] = f"fields($select={select_query})"

    if filter_query:
        params["$filter"] = filter_query

    return _get_paginated(
        url,
        headers=_get_graph_headers({"Prefer": GRAPH_PREFER_OPTIONAL}),
        context="get sharepoint list items",
        params=params,
    )


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
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items/{item_id}"

    response = _make_request(
        method="GET",
        url=url,
        headers=_get_graph_headers({"Prefer": GRAPH_PREFER_OPTIONAL}),
        context="get sharepoint list item",
    )

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
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items"

    response = _make_request(
        method="POST",
        url=url,
        headers=_get_graph_headers(),
        context="create sharepoint list item",
        json={"fields": field_data},
    )

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
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items/{item_id}"

    _make_request(
        method="DELETE",
        url=url,
        headers=_get_graph_headers(),
        context="delete sharepoint list item",
    )


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
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/lists/{list_id}/items/{item_id}/fields"

    _make_request(
        method="PATCH",
        url=url,
        headers=_get_graph_headers(),
        context="update sharepoint list item",
        json=field_data,
    )


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
    # Construct the URL for the ensure user endpoint
    url = f"{site_url}/_api/lists/getByTitle('{list_name}')/items({item_id})?$select=AttachmentFiles,Title&$expand=AttachmentFiles"

    response = _make_request(
        method="GET",
        url=url,
        headers=_get_sp_headers(),
        context="get list attachments",
    )

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
        file_url = (
            f"{site_url}/_api/Web/GetFileByServerRelativeUrl('{relative_url}')/$value"
        )

        attachment_response = _make_request(
            method="GET",
            url=file_url,
            headers=_get_sp_headers(),
            context="download list attachment",
        )

        return {
            "name": attachment.get("FileName"),
            "url": attachment.get("ServerRelativeUrl"),
            "data": attachment_response.content,
        }

    return [download_attachment(x) for x in attachments]
