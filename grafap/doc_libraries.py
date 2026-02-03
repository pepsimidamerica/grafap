"""
Module contains functionality for working with document libraries/drives.
"""

import logging
import os
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests
from grafap._auth import Decorators
from grafap._constants import (
    DEFAULT_TIMEOUT,
    FILE_OPERATION_TIMEOUT,
    ODATA_NEXT_LINK,
    ODATA_VALUE,
)
from grafap._helpers import (
    _basic_retry,
    _check_env,
    _get_graph_headers,
    _get_sp_headers,
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

    all_drives = []

    while True:
        try:
            response = requests.get(
                url,
                headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error {e.response.status_code}, could not get document libraries: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not get document libraries: {e}"
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not get document libraries: {e}")
            raise Exception(f"Error, could not get document libraries: {e}") from e

        data = response.json()
        all_drives.extend(data.get(ODATA_VALUE, []))
        if ODATA_NEXT_LINK in data:
            url = data[ODATA_NEXT_LINK]
        else:
            break

    return all_drives


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

    all_items = []

    while True:
        try:
            response = requests.get(
                url,
                headers=_get_graph_headers(),
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error {e.response.status_code}, could not get document library items: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not get document library items: {e}"
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not get document library items: {e}")
            raise Exception(f"Error, could not get document library items: {e}") from e

        data = response.json()
        all_items.extend(data.get(ODATA_VALUE, []))
        if ODATA_NEXT_LINK in data:
            url = data[ODATA_NEXT_LINK]
        else:
            break

    return all_items


@Decorators._refresh_sp_token
def doclib_file_return(file_url: str) -> dict:
    """
    Downloads a file from a SharePoint site, likely stored in a document library.

    :param file_url: The direct URL to the file in the SharePoint document library
    :type file_url: str
    :return: A dictionary containing the file name, URL, and file content
    """
    # Parse the file URL to get the site URL and relative URL
    parsed_url = urlparse(file_url)
    path_parts = parsed_url.path.split("/")
    site_path = "/".join(path_parts[:3])  # This will include the site path
    relative_url = "/".join(path_parts[3:])  # This will include the rest of the path

    site_url = f"{parsed_url.scheme}://{parsed_url.netloc}{site_path}"

    try:
        response = requests.get(
            f"{site_url}/_api/Web/GetFileByUrl(@url)/$value?@url='{file_url}'",
            headers=_get_sp_headers(),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error {e.response.status_code}, could not download file: {e}")
        raise Exception(
            f"Error {e.response.status_code}, could not download file: {e}"
        ) from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not download file: {e}")
        raise Exception(f"Error, could not download file: {e}") from e

    file_name = relative_url.split("/")[-1]

    return {"name": file_name, "url": file_url, "data": response.content}


@Decorators._refresh_sp_token
def doclib_folder_create(site_url: str, folder_path: str) -> dict:
    """
    Creates a new folder in sharepoint, likely within a document library.

    :param site_url: The SharePoint site URL (e.g. https://tenant.sharepoint.com/sites/site)
    :type site_url: str
    :param folder_path: Folder path relative to the site, or a server-relative path
    :type folder_path: str
    :return: Details about the created folder
    :rtype: dict
    """
    parsed_url = urlparse(site_url)
    site_path = PurePosixPath(parsed_url.path)
    normalized_folder_path = PurePosixPath(str(folder_path).replace("\\", "/"))

    if str(normalized_folder_path).startswith("/"):
        server_relative_path = normalized_folder_path
    else:
        server_relative_path = site_path / normalized_folder_path

    server_relative_path = PurePosixPath("/" + str(server_relative_path).lstrip("/"))

    @_basic_retry
    def create_folder(folder_server_relative_url: str) -> None:
        response = requests.post(
            f"{site_url}/_api/web/folders",
            headers=_get_sp_headers(),
            json={
                "__metadata": {"type": "SP.Folder"},
                "ServerRelativeUrl": folder_server_relative_url,
            },
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code in {200, 201}:
            return

        if response.status_code in {409, 500}:
            response_text = response.text.lower()
            if "already exists" in response_text or "already exist" in response_text:
                return

        response.raise_for_status()

    path_parts = [part for part in server_relative_path.parts if part not in {"/", ""}]
    current_path = PurePosixPath("/")
    for part in path_parts:
        current_path = current_path / part
        try:
            create_folder(str(current_path))
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error {e.response.status_code}, could not create folder: {e}"
            )
            raise Exception(
                f"Error {e.response.status_code}, could not create folder: {e}"
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Error, could not create folder: {e}")
            raise Exception(f"Error, could not create folder: {e}") from e

    return {
        "ServerRelativeUrl": str(server_relative_path),
        "Name": server_relative_path.name,
        "FullPath": str(server_relative_path),
    }


@Decorators._refresh_sp_token
def doclib_file_create(
    site_url: str,
    folder_path: str,
    file_name: str,
    file_content: bytes,
    overwrite: bool = True,
) -> dict:
    """
    Uploads a file to sharepoint, likely to a document library.

    :param site_url: The SharePoint site URL (e.g. https://tenant.sharepoint.com/sites/site)
    :type site_url: str
    :param folder_path: Folder path relative to the site, or a server-relative path
    :type folder_path: str
    :param file_name: File name to upload
    :type file_name: str
    :param file_content: File content as bytes
    :type file_content: bytes
    :param overwrite: If True, overwrite existing file
    :type overwrite: bool
    :return: Details about the uploaded file
    :rtype: dict
    """
    parsed_url = urlparse(site_url)
    site_path = PurePosixPath(parsed_url.path)
    normalized_folder_path = PurePosixPath(str(folder_path).replace("\\", "/"))

    if str(normalized_folder_path).startswith("/"):
        server_relative_path = normalized_folder_path
    else:
        server_relative_path = site_path / normalized_folder_path

    server_relative_path = PurePosixPath("/" + str(server_relative_path).lstrip("/"))

    upload_url = (
        f"{site_url}/_api/web/GetFolderByServerRelativeUrl('{server_relative_path}')"
        f"/Files/add(url='{file_name}',overwrite={str(overwrite).lower()})"
    )

    try:
        response = requests.post(
            upload_url,
            headers=_get_sp_headers({"Content-Type": "application/octet-stream"}),
            data=file_content,
            timeout=FILE_OPERATION_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error {e.response.status_code}, could not upload file: {e}")
        raise Exception(
            f"Error {e.response.status_code}, could not upload file: {e}"
        ) from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not upload file: {e}")
        raise Exception(f"Error, could not upload file: {e}") from e

    data = response.json().get("d", {})
    return {
        "name": data.get("Name", file_name),
        "ServerRelativeUrl": data.get(
            "ServerRelativeUrl", f"{server_relative_path}/{file_name}"
        ),
        "TimeCreated": data.get("TimeCreated"),
        "TimeLastModified": data.get("TimeLastModified"),
        "Length": data.get("Length"),
    }


@Decorators._refresh_sp_token
def doclib_file_delete(file_url: str) -> None:
    """
    Deletes a file from a SharePoint site, likley stored in a document library.

    :param file_url: The direct URL to the file in the SharePoint document library
    :type file_url: str
    :return: None
    :rtype: None
    """
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
            headers=_get_sp_headers(),
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error {e.response.status_code}, could not delete file: {e}")
        raise Exception(
            f"Error {e.response.status_code}, could not delete file: {e}"
        ) from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not delete file: {e}")
        raise Exception(f"Error, could not delete file: {e}") from e
