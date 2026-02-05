"""
Module contains functionality for working with document libraries/drives.
"""

import logging
import os
from typing import Literal

from grafap._auth import Decorators
from grafap._constants import FILE_OPERATION_TIMEOUT
from grafap._helpers import (
    _check_env,
    _get_graph_headers,
    _get_paginated,
    _make_request,
)

logger = logging.getLogger(__name__)


@Decorators._refresh_graph_token
def doclibs_return(site_id: str) -> list[dict]:
    """
    Returns a list of all document libraries/drives for a given SharePoint site.

    :param site_id: The SharePoint site ID
    :type site_id: str
    :return: A list of document libraries/drives
    :rtype: list[dict]
    """
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/drives"

    return _get_paginated(
        url,
        headers=_get_graph_headers(),
        context="get document libraries",
    )


@Decorators._refresh_graph_token
def doclib_items_return(
    site_id: str, doclib_id: str, subfolder_id: str | None = None
) -> list[dict]:
    """
    Returns a listing of all items (files or subfolders) in a given document library/drive.
    Optionally, include a subfolder ID to return items within that subfolder.

    :param site_id: The SharePoint site ID
    :type site_id: str
    :param doclib_id: The document library/drive ID
    :type doclib_id: str
    :param subfolder_id: The subfolder ID within the document library/drive
    :type subfolder_id: str | None
    :return: A list of items (files or subfolders) in the document library/drive
    :rtype: list[dict]
    """
    _check_env("GRAPH_BASE_URL")

    if subfolder_id:
        url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/drives/{doclib_id}/items/{subfolder_id}/children"
    else:
        url = (
            f"{os.environ['GRAPH_BASE_URL']}{site_id}/drives/{doclib_id}/root/children"
        )

    return _get_paginated(
        url,
        headers=_get_graph_headers(),
        context="get document library items",
    )


@Decorators._refresh_graph_token
def doclib_file_return(site_id: str, item_id: str) -> dict:
    """
    Downloads a file from a SharePoint site, likely stored in a document library.

    :param site_id: The SharePoint site ID
    :type site_id: str
    :param item_id: The ID of the file to download
    :type item_id: str
    :return: A dictionary containing the file name, URL, and file content
    """
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/drive/items/{item_id}/content"

    response = _make_request(
        method="GET",
        url=url,
        headers=_get_graph_headers(),
        context="download file",
        timeout=FILE_OPERATION_TIMEOUT,
    )

    if response.status_code != 200:
        logger.error(
            f"Error {response.status_code}, could not download file: {response.text}"
        )
        raise Exception(
            f"Error {response.status_code}, could not download file: {response.text}"
        )

    return {
        "file_name": response.headers.get("Content-Disposition", "").split("filename=")[
            -1
        ],
        "file_url": response.url,
        "file_content": response.content,
    }


@Decorators._refresh_graph_token
def doclib_folder_create(
    site_id: str,
    folder_name: str,
    parent_id: str = "root",
    conflict_behavior: Literal["rename", "replace", "fail"] = "fail",
) -> dict:
    """
    Creates a new folder in sharepoint, likely within a document library.

    :param site_id: The SharePoint site ID
    :type site_id: str
    :param folder_name: The name of the folder to create
    :type folder_name: str
    :param parent_id: The ID of the parent folder to create this new folder under ("root" to create the the folder at the top-level of the document library)
    :type parent_id: str
    :param conflict_behavior: Behavior if a folder with the same name exists
                              ("rename", "replace", or "fail")
    :type conflict_behavior: Literal["rename", "replace", "fail"]
    :return: Details about the created folder
    :rtype: dict
    """
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/drive/items/{parent_id}/children"
    response = _make_request(
        method="POST",
        url=url,
        headers=_get_graph_headers(),
        json={
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": conflict_behavior,
        },
        context="create folder",
        timeout=FILE_OPERATION_TIMEOUT,
    )

    if response.status_code != 201:
        logger.error(
            f"Error {response.status_code}, could not create folder: {response.text}"
        )
        raise Exception(
            f"Error {response.status_code}, could not create folder: {response.text}"
        )

    return response.json()


@Decorators._refresh_graph_token
def doclib_file_create(
    site_id: str,
    file_name: str,
    file_content: bytes,
    content_type: str,
    parent_id: str = "root",
) -> dict:
    """
    Uploads a file to sharepoint, likely to a document library.

    :param site_id: The SharePoint site ID
    :type site_id: str
    :param file_name: The name of the file to upload
    :type file_name: str
    :param file_content: The content of the file to upload
    :type file_content: bytes
    :param content_type: The MIME type of the file
    :type content_type: str
    :param parent_id: The ID of the parent folder to upload the file to ("root" to upload the file to the top-level of the document library)
    :type parent_id: str
    :return: Details about the uploaded file
    :rtype: dict
    """
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/drive/items/{parent_id}:/{file_name}:/content"

    response = _make_request(
        method="PUT",
        url=url,
        headers=_get_graph_headers({"Content-Type": content_type}),
        data=file_content,
        context="upload file",
        timeout=FILE_OPERATION_TIMEOUT,
    )

    if response.status_code != 201:
        logger.error(
            f"Error {response.status_code}, could not upload file: {response.text}"
        )
        raise Exception(
            f"Error {response.status_code}, could not upload file: {response.text}"
        )

    return response.json()


@Decorators._refresh_graph_token
def doclib_file_delete(site_id: str, item_id: str) -> None:
    """
    Deletes a file from a SharePoint site, likley stored in a document library.

    :param site_id: The SharePoint site ID
    :type site_id: str
    :param item_id: The ID of the file to delete
    :type item_id: str
    :return: None
    :rtype: None
    """
    _check_env("GRAPH_BASE_URL")

    url = f"{os.environ['GRAPH_BASE_URL']}{site_id}/drive/items/{item_id}"

    response = _make_request(
        method="DELETE",
        url=url,
        headers=_get_graph_headers(),
        context="delete file",
        timeout=FILE_OPERATION_TIMEOUT,
    )

    if response.status_code != 204:
        logger.error(
            f"Error {response.status_code}, could not delete file: {response.text}"
        )
        raise Exception(
            f"Error {response.status_code}, could not delete file: {response.text}"
        )
