"""
Core GrafapClient class providing async-first access to Microsoft Graph
and SharePoint REST APIs.

Uses httpx2 under the hood for both sync (via asyncio.run proxy) and
async HTTP requests.
"""

import asyncio
import base64
import functools
import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx2 as httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from grafap._constants import (
    DEFAULT_TIMEOUT,
    FILE_OPERATION_TIMEOUT,
    GRAPH_PREFER_OPTIONAL,
    ODATA_NEXT_LINK,
    ODATA_VALUE,
    USER_INFO_LIST_NAME,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)
_basic_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)


# ---------------------------------------------------------------------------
# Standalone helpers
# ---------------------------------------------------------------------------


def _check_env(key: str, default: str | None = None) -> str:
    """
    Checks if a given env var has been set. Raises an error if it hasn't been
    with instructions to read the README.md for setup instructions.

    :param key: The environment variable key to check
    :type key: str
    :param default: Optional default value if the env var is not set
    :type default: str | None
    :return: The value of the environment variable
    :rtype: str
    :raises OSError: If the environment variable is not set and no default is provided
    """
    value = os.environ.get(key, default)
    if value is None:
        raise OSError(
            f"Missing required environment variable: {key}\n"
            f"Please see README.md for configuration instructions."
        )
    return value


# ---------------------------------------------------------------------------
# Sync proxy
# ---------------------------------------------------------------------------
class _SyncProxy:
    """
    Transparent synchronous proxy that wraps every async method on a
    GrafapClient instance so it can be called without await.

    Uses asyncio.run() internally, acceptable overhead given that
    the dominant latency comes from the network round-trip itself.
    """

    def __init__(self, client: "GrafapClient") -> None:
        self._client = client

    def __getattr__(self, name: str):
        attr = getattr(self._client, name)
        if not callable(attr):
            return attr

        @functools.wraps(attr)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # asyncio.run() creates event loop each call, so the
            # cached httpx.AsyncClient must be
            # discarded to avoid "Event loop is closed" errors.
            self._client._http_client = None
            return asyncio.run(attr(*args, **kwargs))

        # Cache on the instance so the functools wrapper is only created once
        # per attribute name.
        setattr(self, name, sync_wrapper)
        return sync_wrapper


# ---------------------------------------------------------------------------
# GrafapClient
# ---------------------------------------------------------------------------
class GrafapClient:
    """
    Async-first client for Microsoft Graph and SharePoint REST APIs.

    All endpoint methods are async. For synchronous usage, access them
    through the sync proxy.

    client = GrafapClient(tenant_id=..., client_id=..., client_secret=...)

    sites = await client.sites_return()
    # or
    sites = client.sync.sites_return()

    :param tenant_id: Azure AD tenant ID.
    :type tenant_id: str
    :param client_id: Application (client) ID for Graph API authentication.
    :type client_id: str
    :param client_secret: Client secret for Graph API authentication (client-credentials flow).
    :type client_secret: str | None
    :param graph_base_url: Base URL for Microsoft Graph site-scoped requests.
    :type graph_base_url: str
    :param graph_login_base_url: Base URL for the Graph login endpoint.
    :type graph_login_base_url: str
    :param graph_scopes: OAuth scopes for the Graph token request.
    :type graph_scopes: str
    :param graph_grant_type: OAuth grant type for the Graph token request.
    :type graph_grant_type: str
    :param sp_client_id: Client ID for SharePoint REST API auth (defaults to *client_id*).
    :type sp_client_id: str | None
    :param sp_certificate_path: Path to the PFX certificate for SharePoint REST API auth.
    :type sp_certificate_path: str | None
    :param sp_certificate_password: Password for the PFX certificate.
    :type sp_certificate_password: str | None
    :param sp_login_base_url: Base URL for the SharePoint login endpoint.
    :type sp_login_base_url: str
    :param sp_scopes: OAuth scopes for the SharePoint token request.
    :type sp_scopes: str | None
    :param sp_grant_type: OAuth grant type for the SharePoint token request.
    :type sp_grant_type: str
    :param sp_site: SharePoint site hostname used to build the default SP scope.
    :type sp_site: str | None
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str | None = None,
        graph_base_url: str = "https://graph.microsoft.com/v1.0/sites/",
        graph_login_base_url: str = "https://login.microsoftonline.com/",
        graph_scopes: str = "https://graph.microsoft.com/.default",
        graph_grant_type: str = "client_credentials",
        sp_client_id: str | None = None,
        sp_certificate_path: str | None = None,
        sp_certificate_password: str | None = None,
        sp_login_base_url: str = "https://login.microsoftonline.com/",
        sp_scopes: str | None = None,
        sp_grant_type: str = "client_credentials",
        sp_site: str | None = None,
    ) -> None:
        """
        Initialize the GrafapClient with the given credentials and settings.
        """
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._graph_base_url = graph_base_url
        self._graph_login_base_url = graph_login_base_url
        self._graph_scopes = graph_scopes
        self._graph_grant_type = graph_grant_type

        self._sp_client_id = sp_client_id or client_id
        self._sp_certificate_path = sp_certificate_path
        self._sp_certificate_password = sp_certificate_password
        self._sp_login_base_url = sp_login_base_url
        self._sp_scopes = sp_scopes
        if sp_site and not sp_scopes:
            self._sp_scopes = f"https://{sp_site}.sharepoint.com/.default"
        self._sp_grant_type = sp_grant_type
        self._sp_site = sp_site

        self._graph_token: str | None = None
        self._graph_token_expires_at: datetime | None = None
        self._sp_token: str | None = None
        self._sp_token_expires_at: datetime | None = None

        self._http_client: httpx.AsyncClient | None = None

    @property
    def sync(self) -> _SyncProxy:
        """
        Return a synchronous proxy that wraps every async method.
        """
        return _SyncProxy(self)

    async def close(self) -> None:
        """
        Close the underlying HTTP client and release resources.
        """
        if self._http_client is not None:
            try:
                await self._http_client.aclose()
            except RuntimeError:
                logger.debug("HTTP client already closed; discarding reference.")
            self._http_client = None

    @classmethod
    def from_env(cls) -> "GrafapClient":
        """
        Build a GrafapClient from environment variables.

        Reads the same variables that the pre-2.0 module-level funcs
        expected (GRAPH_TENANT_ID, GRAPH_CLIENT_ID...). Convenience func.
        """
        return cls(
            tenant_id=_check_env("GRAPH_TENANT_ID"),
            client_id=_check_env("GRAPH_CLIENT_ID"),
            client_secret=_check_env("GRAPH_CLIENT_SECRET"),
            graph_base_url=os.environ.get(
                "GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0/sites/"
            ),
            graph_login_base_url=os.environ.get(
                "GRAPH_LOGIN_BASE_URL", "https://login.microsoftonline.com/"
            ),
            graph_scopes=os.environ.get(
                "GRAPH_SCOPES", "https://graph.microsoft.com/.default"
            ),
            graph_grant_type=os.environ.get("GRAPH_GRANT_TYPE", "client_credentials"),
            sp_client_id=os.environ.get("SP_CLIENT_ID"),
            sp_certificate_path=os.environ.get("SP_CERTIFICATE_PATH"),
            sp_certificate_password=os.environ.get("SP_CERTIFICATE_PASSWORD"),
            sp_login_base_url=os.environ.get(
                "SP_LOGIN_BASE_URL", "https://login.microsoftonline.com/"
            ),
            sp_scopes=os.environ.get("SP_SCOPES"),
            sp_grant_type=os.environ.get("SP_GRANT_TYPE", "client_credentials"),
            sp_site=os.environ.get("SP_SITE"),
        )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Lazily create shared httpx.AsyncClient.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    async def _ensure_graph_token(self) -> str:
        """
        Return a valid Graph API bearer token, refreshing it if the
        cached token is missing or expired.
        """
        now = datetime.now()
        if (
            self._graph_token
            and self._graph_token_expires_at
            and self._graph_token_expires_at > now
        ):
            return self._graph_token

        logger.info("Getting Microsoft Graph bearer token...")
        client = await self._get_http_client()

        response = await client.post(
            f"{self._graph_login_base_url}{self._tenant_id}/oauth2/v2.0/token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": self._graph_grant_type,
                "scope": self._graph_scopes,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        self._graph_token = data["access_token"]
        self._graph_token_expires_at = now + timedelta(seconds=data["expires_in"])
        return self._graph_token

    async def _ensure_sp_token(self) -> str:
        """
        Return a valid SharePoint REST API bearer token, refreshing it if
        the cached token is missing or expired.
        """
        now = datetime.now()
        if (
            self._sp_token
            and self._sp_token_expires_at
            and self._sp_token_expires_at > now
        ):
            return self._sp_token

        if not self._sp_certificate_path or not self._sp_certificate_password:
            raise Exception(
                "SharePoint certificate path and password are required for "
                "SP REST API authentication."
            )

        logger.info("Getting SharePoint REST API bearer token...")

        # Load the PFX certificate
        with Path(self._sp_certificate_path).open("rb") as cert_file:
            cert_data = cert_file.read()
        pfx = pkcs12.load_key_and_certificates(
            cert_data, str.encode(self._sp_certificate_password)
        )

        private_key = pfx[0]
        certificate = pfx[1]

        if private_key is None or certificate is None:
            raise Exception(
                "Failed to extract private key or certificate from PFX file."
            )

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # SHA-1 thumbprint for the x5t header
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        thumbprint = hashlib.sha1(cert_der).digest()
        thumbprint_b64 = (
            base64.urlsafe_b64encode(thumbprint).decode("utf-8").rstrip("=")
        )

        # JWT client assertion
        payload = {
            "aud": f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token",
            "iss": self._client_id,
            "sub": self._client_id,
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + 600,
        }
        headers = {"x5t": thumbprint_b64}
        jwt_assertion = jwt.encode(
            payload, private_key_pem, algorithm="RS256", headers=headers
        )

        client = await self._get_http_client()
        response = await client.post(
            f"{self._sp_login_base_url}{self._tenant_id}/oauth2/v2.0/token",
            headers=headers,
            data={
                "client_id": self._sp_client_id,
                "grant_type": self._sp_grant_type,
                "scope": self._sp_scopes,
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": jwt_assertion,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        self._sp_token = data["access_token"]
        self._sp_token_expires_at = now + timedelta(seconds=float(data["expires_in"]))
        return self._sp_token

    def _get_graph_headers(self, extra_headers: dict | None = None) -> dict:
        """
        Build request headers for Microsoft Graph API calls.

        :param extra_headers: Optional additional headers to merge.
        :type extra_headers: dict | None
        :return: Complete headers dictionary.
        :rtype: dict
        """
        headers = {"Authorization": f"Bearer {self._graph_token}"}
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _get_sp_headers(self, extra_headers: dict | None = None) -> dict:
        """
        Build request headers for SharePoint REST API calls.

        :param extra_headers: Optional additional headers to merge.
        :type extra_headers: dict | None
        :return: Complete headers dictionary.
        :rtype: dict
        """
        headers = {
            "Authorization": f"Bearer {self._sp_token}",
            "Accept": "application/json;odata=verbose;charset=utf-8",
            "Content-Type": "application/json;odata=verbose;charset=utf-8",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    @_basic_retry
    async def _request(
        self,
        method: str,
        url: str,
        token_type: Literal["graph", "sp"] = "graph",
        headers: dict | None = None,
        context: str = "API request",
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request with automatic token refresh and error handling.

        :param method: HTTP method (GET, POST, PATCH, DELETE, …).
        :type method: str
        :param url: Target URL.
        :type url: str
        :param token_type: Which token to use, "graph" or "sp".
        :type token_type: Literal["graph", "sp"]
        :param headers: Extra headers to merge into the request.
        :type headers: dict | None
        :param context: Human-readable label for error messages.
        :type context: str
        :param kwargs: Additional arguments forwarded to httpx.AsyncClient.request
                       (json, data, params, timeout, …).
        :return: The HTTP response.
        :rtype: httpx.Response
        :raises Exception: For HTTP errors or general request failures.
        """
        # Ensure we have a valid token
        if token_type == "graph":
            await self._ensure_graph_token()
            req_headers = self._get_graph_headers(headers)
        else:
            await self._ensure_sp_token()
            req_headers = self._get_sp_headers(headers)

        client = await self._get_http_client()
        timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)

        try:
            response = await client.request(
                method, url, headers=req_headers, timeout=timeout, **kwargs
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error, {context}: {e}")
            raise Exception(
                f"HTTP {e.response.status_code} error, {context}: {e}"
            ) from e
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.error(f"Connection error during {context}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error during {context}: {e}")
            raise Exception(f"Request error during {context}: {e}") from e

        return response

    async def _get_paginated(
        self,
        url: str,
        token_type: Literal["graph", "sp"] = "graph",
        headers: dict | None = None,
        params: dict | None = None,
        context: str = "API request",
    ) -> list[dict]:
        """
        Fetch all pages from a paginated Graph / SharePoint endpoint.

        Automatically follows @odata.nextLink until exhausted.

        :param url: Initial API endpoint URL.
        :type url: str
        :param token_type: Which token to use, "graph" or "sp".
        :type token_type: Literal["graph", "sp"]
        :param headers: Extra headers for the request.
        :type headers: dict | None
        :param params: Optional query parameters (only sent on the first page).
        :type params: dict | None
        :param context: Human-readable label for logging.
        :type context: str
        :return: Flattened list of all result items across pages.
        :rtype: list[dict]
        """
        all_results: list[dict] = []

        while True:
            response = await self._request(
                method="GET",
                url=url,
                token_type=token_type,
                headers=headers,
                params=params,
                context=context,
            )

            data = response.json()
            all_results.extend(data.get(ODATA_VALUE, []))

            if ODATA_NEXT_LINK not in data:
                break

            url = data[ODATA_NEXT_LINK]
            params = None  # nextLink URLs already include query parameters

        return all_results

    # ---------------------------------------------------------------------------
    # Sites
    # ---------------------------------------------------------------------------

    async def sites_return(self) -> list[dict]:
        """
        Get all site data in the tenant.

        :return: List of site resources.
        :rtype: list[dict]
        """
        return await self._get_paginated(self._graph_base_url, context="get sites")

    # ---------------------------------------------------------------------------
    # Lists
    # ---------------------------------------------------------------------------

    async def lists_return(self, site_id: str) -> list[dict]:
        """
        Get all lists in a given SharePoint site.

        :param site_id: The site ID.
        :type site_id: str
        :return: List of SharePoint lists.
        :rtype: list[dict]
        """
        url = f"{self._graph_base_url}{site_id}/lists"
        return await self._get_paginated(url, context="get sharepoint lists")

    async def list_items_return(
        self,
        site_id: str,
        list_id: str,
        filter_query: str | None = None,
        select_query: str | None = None,
    ) -> list[dict]:
        """
        Get field data from a SharePoint list. If using *filter_query*, the filtered
        column must be indexed in SharePoint list settings or the request will fail.

        :param site_id: The site ID.
        :type site_id: str
        :param list_id: The list ID.
        :type list_id: str
        :param filter_query: Optional OData $filter expression.
        :type filter_query: str | None
        :param select_query: Optional OData $select for fields.
        :type select_query: str | None
        :return: List of list item field data.
        :rtype: list[dict]
        """
        url = f"{self._graph_base_url}{site_id}/lists/{list_id}/items"
        params: dict[str, str] = {"$expand": "fields"}

        if select_query:
            params["$expand"] = f"fields($select={select_query})"
        if filter_query:
            params["$filter"] = filter_query

        return await self._get_paginated(
            url,
            headers={"Prefer": GRAPH_PREFER_OPTIONAL},
            params=params,
            context="get sharepoint list items",
        )

    async def list_item_return(self, site_id: str, list_id: str, item_id: str) -> dict:
        """
        Get field data from a specific SharePoint list item.

        :param site_id: The site ID.
        :type site_id: str
        :param list_id: The list ID.
        :type list_id: str
        :param item_id: The item ID.
        :type item_id: str
        :return: List item field data.
        :rtype: dict
        """
        url = f"{self._graph_base_url}{site_id}/lists/{list_id}/items/{item_id}"
        response = await self._request(
            method="GET",
            url=url,
            headers={"Prefer": GRAPH_PREFER_OPTIONAL},
            context="get sharepoint list item",
        )
        return response.json()

    async def list_item_create(
        self, site_id: str, list_id: str, field_data: dict
    ) -> dict:
        """
        Create a new item in a SharePoint list.

        :param site_id: The site ID.
        :type site_id: str
        :param list_id: The list ID.
        :type list_id: str
        :param field_data: Dictionary of field names to values.
        :type field_data: dict
        :return: The created list item.
        :rtype: dict
        """
        url = f"{self._graph_base_url}{site_id}/lists/{list_id}/items"
        response = await self._request(
            method="POST",
            url=url,
            context="create sharepoint list item",
            json={"fields": field_data},
        )
        return response.json()

    async def list_item_delete(self, site_id: str, list_id: str, item_id: str) -> None:
        """
        Delete an item from a SharePoint list.

        :param site_id: The site ID.
        :type site_id: str
        :param list_id: The list ID.
        :type list_id: str
        :param item_id: The item ID to delete.
        :type item_id: str
        """
        url = f"{self._graph_base_url}{site_id}/lists/{list_id}/items/{item_id}"
        await self._request(
            method="DELETE",
            url=url,
            context="delete sharepoint list item",
        )

    async def list_item_update(
        self,
        site_id: str,
        list_id: str,
        item_id: str,
        field_data: dict[str, Any],
    ) -> None:
        """
        Update fields on a SharePoint list item.

        :param site_id: The site ID.
        :type site_id: str
        :param list_id: The list ID.
        :type list_id: str
        :param item_id: The item ID to update.
        :type item_id: str
        :param field_data: Dictionary of field names to new values (only
            include fields you are changing).
        :type field_data: dict[str, Any]
        """
        url = f"{self._graph_base_url}{site_id}/lists/{list_id}/items/{item_id}/fields"
        await self._request(
            method="PATCH",
            url=url,
            context="update sharepoint list item",
            json=field_data,
        )

    async def list_item_attachments_return(
        self,
        site_url: str,
        list_name: str,
        item_id: int,
        download: bool = False,
    ) -> list[dict]:
        """
        Get attachments for a SharePoint list item.

        Uses the SharePoint REST API (not Graph).

        :param site_url: The site URL (e.g. https://contoso.sharepoint.com/sites/MySite).
        :type site_url: str
        :param list_name: Display name of the SharePoint list.
        :type list_name: str
        :param item_id: The list item ID.
        :type item_id: int
        :param download: If True, download attachment content as bytes.
        :type download: bool
        :return: List of attachment info dicts (or dicts with data if downloading).
        :rtype: list[dict]
        """
        url = (
            f"{site_url}/_api/lists/getByTitle('{list_name}')"
            f"/items({item_id})?$select=AttachmentFiles,Title"
            f"&$expand=AttachmentFiles"
        )

        response = await self._request(
            method="GET",
            url=url,
            token_type="sp",
            context="get list attachments",
        )

        data = response.json().get("d", {})
        attachments = data.get("AttachmentFiles", {}).get("results", [])

        if not download:
            return [
                {
                    "name": str(x.get("FileName")),
                    "url": str(x.get("ServerRelativeUrl")),
                }
                for x in attachments
            ]

        # Download each attachment sequentially
        results: list[dict] = []
        for attachment in attachments:
            relative_url = attachment.get("ServerRelativeUrl")
            file_url = (
                f"{site_url}/_api/Web/"
                f"GetFileByServerRelativeUrl('{relative_url}')/$value"
            )

            attachment_response = await self._request(
                method="GET",
                url=file_url,
                token_type="sp",
                context="download list attachment",
            )

            results.append(
                {
                    "name": attachment.get("FileName"),
                    "url": attachment.get("ServerRelativeUrl"),
                    "data": attachment_response.content,
                }
            )

        return results

    # ---------------------------------------------------------------------------
    # Users
    # ---------------------------------------------------------------------------

    async def ad_users_return(
        self,
        select: str | None = None,
        filter: str | None = None,
        expand: str | None = None,
    ) -> list[dict]:
        """
        Get Azure AD users in the tenant.

        :param select: OData $select query option.
        :type select: str | None
        :param filter: OData $filter query option.
        :type filter: str | None
        :param expand: OData $expand query option.
        :type expand: str | None
        :return: List of user resources.
        :rtype: list[dict]
        """
        params: dict[str, str] = {}
        if select:
            params["$select"] = select
        if filter:
            params["$filter"] = filter
        if expand:
            params["$expand"] = expand

        url = "https://graph.microsoft.com/v1.0/users"
        return await self._get_paginated(
            url=url,
            params=params,
            context="getting AD users",
        )

    async def sp_users_info_return(self, site_id: str) -> list[dict]:
        """
        Query the hidden SharePoint *User Information List* for a site.

        :param site_id: The site ID (use "root" for the root site).
        :type site_id: str
        :return: List of user information entries.
        :rtype: list[dict]
        """
        url = f"{self._graph_base_url}{site_id}/lists('{USER_INFO_LIST_NAME}')/items"
        return await self._get_paginated(
            url,
            params={"expand": "fields(select=Id,Email)"},
        )

    async def sp_user_info_return(
        self,
        site_id: str,
        user_id: str | None = None,
        email: str | None = None,
    ) -> dict:
        """
        Get a specific user from the hidden SharePoint *User Information List*.

        :param site_id: The site ID.
        :type site_id: str
        :param user_id: The user's list item ID.
        :type user_id: str | None
        :param email: The user's email address (used in a $filter).
        :type email: str | None
        :return: User information entry.
        :rtype: dict
        :raises Exception: If the user cannot be found.
        """
        url = f"{self._graph_base_url}{site_id}/lists('{USER_INFO_LIST_NAME}')/items"

        if user_id:
            url += "/" + user_id
        elif email:
            url += "?$filter=fields/UserName eq '" + email + "'"

        response = await self._request(
            method="GET",
            url=url,
            headers={"Prefer": GRAPH_PREFER_OPTIONAL},
            context="getting sharepoint list user data",
        )

        if ODATA_VALUE in response.json():
            if len(response.json()[ODATA_VALUE]) == 0:
                raise Exception("Error, could not find user in sharepoint list")
            return response.json()[ODATA_VALUE][0]
        return response.json()

    async def sp_user_ensure(self, site_url: str, logon_name: str) -> dict:
        """
        Ensure a user exists in a SharePoint site (REST API, not Graph).

        This is necessary so the user can be referenced in People fields
        on that site.

        :param site_url: The site URL.
        :type site_url: str
        :param logon_name: The user's logon name (email address).
        :type logon_name: str
        :return: The ensured user resource.
        :rtype: dict
        """
        url = f"{site_url}/_api/web/ensureuser"
        response = await self._request(
            method="POST",
            url=url,
            token_type="sp",
            context="ensuring sharepoint user",
            json={"logonName": logon_name},
        )

        if response.status_code != 200:
            logger.error(
                f"Error {response.status_code}, could not ensure user: "
                f"{response.content}"
            )
            raise Exception(
                f"Error {response.status_code}, could not ensure user: "
                f"{response.content}"
            )

        return response.json()

    # ---------------------------------------------------------------------------
    # Document Libraries
    # ---------------------------------------------------------------------------

    async def doclibs_return(self, site_id: str) -> list[dict]:
        """
        Return all document libraries (drives) for a SharePoint site.

        :param site_id: The site ID.
        :type site_id: str
        :return: List of drive resources.
        :rtype: list[dict]
        """
        url = f"{self._graph_base_url}{site_id}/drives"
        return await self._get_paginated(url, context="get document libraries")

    async def doclib_items_return(
        self,
        site_id: str,
        doclib_id: str,
        subfolder_id: str | None = None,
    ) -> list[dict]:
        """
        List items (files and folders) in a document library.

        :param site_id: The site ID.
        :type site_id: str
        :param doclib_id: The document library (drive) ID.
        :type doclib_id: str
        :param subfolder_id: Optional subfolder ID to list children of.
        :type subfolder_id: str | None
        :return: List of drive item resources.
        :rtype: list[dict]
        """
        if subfolder_id:
            url = (
                f"{self._graph_base_url}{site_id}/drives/{doclib_id}"
                f"/items/{subfolder_id}/children"
            )
        else:
            url = f"{self._graph_base_url}{site_id}/drives/{doclib_id}/root/children"

        return await self._get_paginated(url, context="get document library items")

    async def doclib_file_return(self, site_id: str, item_id: str) -> dict:
        """
        Download a file from a SharePoint document library.

        :param site_id: The site ID.
        :type site_id: str
        :param item_id: The drive item ID of the file.
        :type item_id: str
        :return: Dict with keys file_name, file_url, file_content.
        :rtype: dict
        """
        url = f"{self._graph_base_url}{site_id}/drive/items/{item_id}/content"

        response = await self._request(
            method="GET",
            url=url,
            context="download file",
            timeout=FILE_OPERATION_TIMEOUT,
        )

        if response.status_code != 200:
            logger.error(
                f"Error {response.status_code}, could not download file: "
                f"{response.text}"
            )
            raise Exception(
                f"Error {response.status_code}, could not download file: "
                f"{response.text}"
            )

        return {
            "file_name": response.headers.get("Content-Disposition", "").split(
                "filename="
            )[-1],
            "file_url": str(response.url),
            "file_content": response.content,
        }

    async def doclib_file_via_url_return(self, file_url: str) -> dict:
        """
        Download a file from SharePoint via its full URL.

        Uses the SharePoint REST API (not Graph).

        :param file_url: The direct URL to the file.
        :type file_url: str
        :return: Dict with keys name, url, data.
        :rtype: dict
        """
        parsed_url = urlparse(file_url)
        path_parts = parsed_url.path.split("/")
        site_path = "/".join(path_parts[:3])
        relative_url = "/".join(path_parts[3:])

        site_url = f"{parsed_url.scheme}://{parsed_url.netloc}{site_path}"
        request_url = f"{site_url}/_api/Web/GetFileByUrl(@url)/$value?@url='{file_url}'"

        response = await self._request(
            method="GET",
            url=request_url,
            token_type="sp",
            context="doclib_file_via_url_return",
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(
                f"Error {response.status_code}, could not download file: "
                f"{response.text}"
            )
            raise Exception(
                f"Error {response.status_code}, could not download file: "
                f"{response.text}"
            )

        file_name = relative_url.split("/")[-1]
        return {"name": file_name, "url": file_url, "data": response.content}

    async def doclib_folder_create(
        self,
        site_id: str,
        folder_name: str,
        parent_id: str = "root",
        conflict_behavior: Literal["rename", "replace", "fail"] = "fail",
    ) -> dict:
        """
        Create a new folder in a SharePoint document library.

        :param site_id: The site ID.
        :type site_id: str
        :param folder_name: Name of the new folder.
        :type folder_name: str
        :param parent_id: Parent folder ID ("root" for top-level).
        :type parent_id: str
        :param conflict_behavior: How to handle name conflicts
            ("rename", "replace", or "fail").
        :type conflict_behavior: Literal["rename", "replace", "fail"]
        :return: The created folder resource.
        :rtype: dict
        """
        url = f"{self._graph_base_url}{site_id}/drive/items/{parent_id}/children"
        response = await self._request(
            method="POST",
            url=url,
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
                f"Error {response.status_code}, could not create folder: "
                f"{response.text}"
            )
            raise Exception(
                f"Error {response.status_code}, could not create folder: "
                f"{response.text}"
            )

        return response.json()

    async def doclib_file_create(
        self,
        site_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
        parent_id: str = "root",
    ) -> dict:
        """
        Upload a file to a SharePoint document library.

        :param site_id: The site ID.
        :type site_id: str
        :param file_name: Name of the file (including extension).
        :type file_name: str
        :param file_content: Binary content of the file.
        :type file_content: bytes
        :param content_type: MIME type of the file.
        :type content_type: str
        :param parent_id: Parent folder ID ("root" for top-level).
        :type parent_id: str
        :return: The created drive item resource.
        :rtype: dict
        """
        url = (
            f"{self._graph_base_url}{site_id}/drive/items"
            f"/{parent_id}:/{file_name}:/content"
        )

        response = await self._request(
            method="PUT",
            url=url,
            headers={"Content-Type": content_type},
            data=file_content,
            context="upload file",
            timeout=FILE_OPERATION_TIMEOUT,
        )

        if response.status_code not in [200, 201]:
            logger.error(
                f"Error {response.status_code}, could not upload file: {response.text}"
            )
            raise Exception(
                f"Error {response.status_code}, could not upload file: {response.text}"
            )

        return response.json()

    async def doclib_file_delete(self, site_id: str, item_id: str) -> None:
        """
        Delete a file from a SharePoint document library.

        :param site_id: The site ID.
        :type site_id: str
        :param item_id: The drive item ID of the file to delete.
        :type item_id: str
        """
        url = f"{self._graph_base_url}{site_id}/drive/items/{item_id}"

        response = await self._request(
            method="DELETE",
            url=url,
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

    # ---------------------------------------------------------------------------
    # Termstore
    # ---------------------------------------------------------------------------

    @_basic_retry
    async def termstore_groups_return(self, site_id: str) -> dict:
        """
        List all termstore group objects in a site.

        :param site_id: The site ID.
        :type site_id: str
        :return: Termstore groups resource.
        :rtype: dict
        """
        response = await self._request(
            method="GET",
            url=f"{self._graph_base_url}{site_id}/termStore/groups",
            context="get termstore groups",
        )
        return response.json()
