"""
Module contains functionality for working with document libraries/drives.
"""

import logging
import os
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests
from grafap._auth import Decorators
from grafap._helpers import _basic_retry

logger = logging.getLogger(__name__)


def doclibs_return(site_id: str):
    """
    Returns a list of all document libraries/drives for a given SharePoint site.
    """
    pass


@Decorators._refresh_sp_token
def doclib_file_return(file_url: str) -> dict:
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
    if "SP_BEARER_TOKEN" not in os.environ:
        raise Exception("Error, could not find SP_BEARER_TOKEN in env")

    parsed_url = urlparse(site_url)
    site_path = PurePosixPath(parsed_url.path)
    normalized_folder_path = PurePosixPath(str(folder_path).replace("\\", "/"))

    if str(normalized_folder_path).startswith("/"):
        server_relative_path = normalized_folder_path
    else:
        server_relative_path = site_path / normalized_folder_path

    server_relative_path = PurePosixPath("/" + str(server_relative_path).lstrip("/"))

    headers = {
        "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
        "Accept": "application/json;odata=verbose;charset=utf-8",
        "Content-Type": "application/json;odata=verbose;charset=utf-8",
    }

    @_basic_retry
    def create_folder(folder_server_relative_url: str) -> None:
        response = requests.post(
            f"{site_url}/_api/web/folders",
            headers=headers,
            json={
                "__metadata": {"type": "SP.Folder"},
                "ServerRelativeUrl": folder_server_relative_url,
            },
            timeout=30,
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
    if "SP_BEARER_TOKEN" not in os.environ:
        raise Exception("Error, could not find SP_BEARER_TOKEN in env")

    parsed_url = urlparse(site_url)
    site_path = PurePosixPath(parsed_url.path)
    normalized_folder_path = PurePosixPath(str(folder_path).replace("\\", "/"))

    if str(normalized_folder_path).startswith("/"):
        server_relative_path = normalized_folder_path
    else:
        server_relative_path = site_path / normalized_folder_path

    server_relative_path = PurePosixPath("/" + str(server_relative_path).lstrip("/"))

    headers = {
        "Authorization": "Bearer " + os.environ["SP_BEARER_TOKEN"],
        "Accept": "application/json;odata=verbose;charset=utf-8",
        "Content-Type": "application/octet-stream",
    }

    upload_url = (
        f"{site_url}/_api/web/GetFolderByServerRelativeUrl('{server_relative_path}')"
        f"/Files/add(url='{file_name}',overwrite={str(overwrite).lower()})"
    )

    try:
        response = requests.post(
            upload_url,
            headers=headers,
            data=file_content,
            timeout=60,
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
        raise Exception(
            f"Error {e.response.status_code}, could not delete file: {e}"
        ) from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Error, could not delete file: {e}")
        raise Exception(f"Error, could not delete file: {e}") from e
