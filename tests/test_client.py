"""
Tests for the grafap GrafapClient.

Uses unittest.mock to intercept HTTP calls at the method level.
Destructive operations (create, update, delete) are tested by verifying the
correct HTTP request is constructed rather than by mutating real data.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx2 as httpx
import pytest
from grafap._client import GrafapClient, _check_env, _SyncProxy
from grafap._constants import (
    USER_INFO_LIST_NAME,
)

# ---------------------------------------------------------------------------
# Helpers for building mock httpx2.Responses
# ---------------------------------------------------------------------------


def _mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    content: bytes = b"",
    headers: dict | None = None,
    url: str = "https://example.com/",
) -> httpx.Response:
    """
    Build a real httpx2.Response for use in mock return values.
    """
    request = httpx.Request("GET", url)
    if json_data is not None:
        content = json.dumps(json_data).encode("utf-8")
        headers = dict(headers or {})
        headers.setdefault("Content-Type", "application/json")
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=headers or {},
        request=request,
    )


# ---------------------------------------------------------------------------
# _check_env
# ---------------------------------------------------------------------------


class TestCheckEnv:
    """
    Tests for the standalone _check_env helper.
    """

    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_VAR", "hello")
        assert _check_env("MY_VAR") == "hello"

    def test_raises_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        with pytest.raises(OSError, match="Missing required environment variable"):
            _check_env("NONEXISTENT_VAR")

    def test_returns_default_when_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        assert _check_env("NONEXISTENT_VAR", default="fallback") == "fallback"


# ---------------------------------------------------------------------------
# _SyncProxy
# ---------------------------------------------------------------------------


class TestSyncProxy:
    """
    Tests for the _SyncProxy that wraps async methods for sync use.
    """

    def test_proxies_async_to_sync(self, client: GrafapClient) -> None:
        proxy = client.sync
        assert isinstance(proxy, _SyncProxy)
        fn = proxy.sites_return
        assert callable(fn)
        assert hasattr(proxy, "sites_return")

    def test_caches_wrapped_methods(self, client: GrafapClient) -> None:
        proxy = client.sync
        first = proxy.lists_return
        second = proxy.lists_return
        assert first is second

    def test_non_callable_attributes_passthrough(self, client: GrafapClient) -> None:
        proxy = client.sync
        assert proxy._client is client


# ---------------------------------------------------------------------------
# GrafapClient
# ---------------------------------------------------------------------------


class TestClientConstruction:
    """
    Tests for GrafapClient instantiation and configuration.
    """

    def test_defaults(self) -> None:
        client = GrafapClient(tenant_id="t", client_id="c")
        assert client._tenant_id == "t"
        assert client._client_id == "c"
        assert client._graph_base_url == "https://graph.microsoft.com/v1.0/sites/"
        assert client._graph_login_base_url == "https://login.microsoftonline.com/"
        assert client._graph_scopes == "https://graph.microsoft.com/.default"
        assert client._graph_grant_type == "client_credentials"

    def test_sp_client_id_defaults_to_client_id(self) -> None:
        client = GrafapClient(tenant_id="t", client_id="c")
        assert client._sp_client_id == "c"

    def test_sp_client_id_explicit(self) -> None:
        client = GrafapClient(tenant_id="t", client_id="c", sp_client_id="sp-c")
        assert client._sp_client_id == "sp-c"

    def test_sp_scopes_auto_derived_from_site(self) -> None:
        client = GrafapClient(tenant_id="t", client_id="c", sp_site="contoso")
        assert client._sp_scopes == "https://contoso.sharepoint.com/.default"

    def test_sp_scopes_explicit_overrides_auto(self) -> None:
        client = GrafapClient(
            tenant_id="t", client_id="c", sp_site="contoso", sp_scopes="custom"
        )
        assert client._sp_scopes == "custom"

    def test_token_cache_starts_empty(self, client: GrafapClient) -> None:
        assert client._graph_token is None
        assert client._graph_token_expires_at is None
        assert client._sp_token is None
        assert client._sp_token_expires_at is None

    def test_http_client_starts_none(self, client: GrafapClient) -> None:
        assert client._http_client is None


# ---------------------------------------------------------------------------
# GrafapClient.from_env
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("clean_env")
class TestFromEnv:
    """
    Tests for GrafapClient.from_env().
    """

    def test_requires_required_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GRAPH_TENANT_ID", "t")
        monkeypatch.setenv("GRAPH_CLIENT_ID", "c")
        with pytest.raises(OSError, match="GRAPH_CLIENT_SECRET"):
            GrafapClient.from_env()

    def test_reads_all_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GRAPH_TENANT_ID", "t")
        monkeypatch.setenv("GRAPH_CLIENT_ID", "c")
        monkeypatch.setenv("GRAPH_CLIENT_SECRET", "s")
        monkeypatch.setenv("GRAPH_BASE_URL", "https://custom.graph.url/")
        monkeypatch.setenv("SP_CLIENT_ID", "sp-c")
        monkeypatch.setenv("SP_CERTIFICATE_PATH", "/path/cert.pfx")
        monkeypatch.setenv("SP_CERTIFICATE_PASSWORD", "pw")
        monkeypatch.setenv("SP_SITE", "mysite")

        client = GrafapClient.from_env()
        assert client._tenant_id == "t"
        assert client._client_id == "c"
        assert client._client_secret == "s"
        assert client._graph_base_url == "https://custom.graph.url/"
        assert client._sp_client_id == "sp-c"
        assert client._sp_certificate_path == "/path/cert.pfx"
        assert client._sp_certificate_password == "pw"
        assert client._sp_site == "mysite"
        assert client._sp_scopes == "https://mysite.sharepoint.com/.default"


# ---------------------------------------------------------------------------
# Header builders
# ---------------------------------------------------------------------------


class TestHeaders:
    """
    Tests for _get_graph_headers and _get_sp_headers.
    """

    def test_graph_headers_bearer_token(self, client: GrafapClient) -> None:
        client._graph_token = "fake-graph-token"
        headers = client._get_graph_headers()
        assert headers["Authorization"] == "Bearer fake-graph-token"

    def test_graph_headers_extra(self, client: GrafapClient) -> None:
        client._graph_token = "t"
        headers = client._get_graph_headers({"Prefer": "foo"})
        assert headers["Authorization"] == "Bearer t"
        assert headers["Prefer"] == "foo"

    def test_sp_headers_bearer_token(self, client: GrafapClient) -> None:
        client._sp_token = "fake-sp-token"
        headers = client._get_sp_headers()
        assert headers["Authorization"] == "Bearer fake-sp-token"
        assert headers["Accept"] == "application/json;odata=verbose;charset=utf-8"
        assert headers["Content-Type"] == "application/json;odata=verbose;charset=utf-8"

    def test_sp_headers_extra(self, client: GrafapClient) -> None:
        client._sp_token = "t"
        headers = client._get_sp_headers({"X-Custom": "val"})
        assert headers["X-Custom"] == "val"


# ---------------------------------------------------------------------------
# _request mocked HTTP
# ---------------------------------------------------------------------------


class TestRequest:
    """
    Tests for the internal _request method using mocked httpx.AsyncClient.
    """

    @pytest.mark.asyncio
    async def test_get_request(self, client: GrafapClient) -> None:
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.return_value = _mock_response(
            200, json_data={"key": "value"}
        )
        client._http_client = mock_client

        response = await client._request("GET", "https://example.com/endpoint")
        assert response.json() == {"key": "value"}
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "https://example.com/endpoint"

    @pytest.mark.asyncio
    async def test_post_with_json_body(self, client: GrafapClient) -> None:
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.return_value = _mock_response(201, json_data={"id": 1})
        client._http_client = mock_client

        response = await client._request(
            "POST", "https://example.com/endpoint", json={"name": "test"}
        )
        assert response.json() == {"id": 1}
        call_kwargs = mock_client.request.call_args.kwargs
        assert call_kwargs["json"] == {"name": "test"}

    @pytest.mark.asyncio
    async def test_http_error_raises(self, client: GrafapClient) -> None:
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.return_value = _mock_response(
            404, json_data={"error": "not found"}
        )
        client._http_client = mock_client

        with pytest.raises(Exception, match="HTTP 404 error"):
            await client._request("GET", "https://example.com/endpoint")

    @pytest.mark.asyncio
    async def test_connection_error_raises(self, client: GrafapClient) -> None:
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ConnectError("boom")
        client._http_client = mock_client

        # The tenacity retry decorator wraps the final exception in RetryError
        from tenacity import RetryError

        with pytest.raises(RetryError):
            await client._request("GET", "https://example.com/endpoint")

    @pytest.mark.asyncio
    async def test_sp_token_type(self, client: GrafapClient) -> None:
        client._sp_token = "sp-tok"
        client._sp_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.return_value = _mock_response(200, json_data={"ok": True})
        client._http_client = mock_client

        response = await client._request(
            "GET", "https://example.com/sp-api", token_type="sp"
        )
        assert response.json() == {"ok": True}
        call_kwargs = mock_client.request.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer sp-tok"

    @pytest.mark.asyncio
    async def test_custom_timeout(self, client: GrafapClient) -> None:
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.return_value = _mock_response(200, json_data={})
        client._http_client = mock_client

        await client._request("GET", "https://example.com/endpoint", timeout=30)
        call_kwargs = mock_client.request.call_args.kwargs
        assert call_kwargs["timeout"] == 30

    @pytest.mark.asyncio
    async def test_token_refresh_on_expiry(self, client: GrafapClient) -> None:
        """
        When the graph token is expired, _ensure_graph_token should refresh it.
        """
        client._graph_token = "old-token"
        client._graph_token_expires_at = datetime.now() - timedelta(hours=1)

        mock_client = AsyncMock()
        # _ensure_graph_token calls client.post(), _request calls client.request()
        mock_client.post.return_value = _mock_response(
            200,
            json_data={"access_token": "new-token", "expires_in": 3600},
        )
        mock_client.request.return_value = _mock_response(200, json_data={"ok": True})
        client._http_client = mock_client

        await client._request("GET", "https://example.com/endpoint")

        assert client._graph_token == "new-token"
        mock_client.post.assert_called_once()
        mock_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# _get_paginated mocked HTTP
# ---------------------------------------------------------------------------


class TestGetPaginated:
    """
    Tests for the internal _get_paginated method.
    """

    @pytest.mark.asyncio
    async def test_single_page(self, client: GrafapClient) -> None:
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.return_value = _mock_response(
            200, json_data={"value": [{"id": 1}, {"id": 2}]}
        )
        client._http_client = mock_client

        results = await client._get_paginated("https://example.com/items")
        assert results == [{"id": 1}, {"id": 2}]

    @pytest.mark.asyncio
    async def test_multiple_pages(self, client: GrafapClient) -> None:
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.side_effect = [
            _mock_response(
                200,
                json_data={
                    "value": [{"id": 1}],
                    "@odata.nextLink": "https://example.com/items?$skip=1",
                },
            ),
            _mock_response(200, json_data={"value": [{"id": 2}]}),
        ]
        client._http_client = mock_client

        results = await client._get_paginated("https://example.com/items")
        assert results == [{"id": 1}, {"id": 2}]
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_result(self, client: GrafapClient) -> None:
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.return_value = _mock_response(200, json_data={"value": []})
        client._http_client = mock_client

        results = await client._get_paginated("https://example.com/items")
        assert results == []

    @pytest.mark.asyncio
    async def test_passes_params_on_first_request_only(
        self, client: GrafapClient
    ) -> None:
        """
        Params should only be sent on the first page request.
        """
        client._graph_token = "tok"
        client._graph_token_expires_at = datetime.now() + timedelta(hours=1)
        mock_client = AsyncMock()
        mock_client.request.side_effect = [
            _mock_response(
                200,
                json_data={
                    "value": [{"id": 1}],
                    "@odata.nextLink": "https://example.com/items?$skip=1",
                },
            ),
            _mock_response(200, json_data={"value": [{"id": 2}]}),
        ]
        client._http_client = mock_client

        await client._get_paginated(
            "https://example.com/items", params={"$filter": "x eq 1"}
        )

        # First request should have params
        call1 = mock_client.request.call_args_list[0]
        assert call1.kwargs["params"] == {"$filter": "x eq 1"}
        # Second request should NOT have params (nextLink encodes them)
        call2 = mock_client.request.call_args_list[1]
        assert call2.kwargs["params"] is None


# ---------------------------------------------------------------------------
# Endpoint methods URL construction via _request / _get_paginated mocking
# ---------------------------------------------------------------------------

BASE = "https://graph.microsoft.com/v1.0/sites/"


class TestSitesReturn:
    """
    Test cases for the sites_return method.
    """

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = [{"id": "s1"}]
            result = await client.sites_return()
            mock_paginated.assert_called_once_with(BASE, context="get sites")
            assert result == [{"id": "s1"}]


class TestListsReturn:
    """
    Test cases for the lists_return method.
    """

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = [{"name": "List1"}]
            result = await client.lists_return("site-123")
            mock_paginated.assert_called_once_with(
                f"{BASE}site-123/lists", context="get sharepoint lists"
            )
            assert result == [{"name": "List1"}]


class TestListItemsReturn:
    """
    Test cases for the list_items_return method.
    """

    @pytest.mark.asyncio
    async def test_basic_call(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = []
            await client.list_items_return("site-123", "list-456")
            call_args = mock_paginated.call_args[0]
            call_kwargs = mock_paginated.call_args.kwargs
            assert call_args[0] == f"{BASE}site-123/lists/list-456/items"
            assert call_kwargs["params"] == {"$expand": "fields"}

    @pytest.mark.asyncio
    async def test_with_filter_and_select(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = []
            await client.list_items_return(
                "site-123",
                "list-456",
                filter_query="fields/Title eq 'test'",
                select_query="Title,Id",
            )
            call_kwargs = mock_paginated.call_args.kwargs
            assert call_kwargs["params"]["$filter"] == "fields/Title eq 'test'"
            assert call_kwargs["params"]["$expand"] == "fields($select=Title,Id)"


class TestListItemReturn:
    """
    Test cases for the list_item_return method.
    """

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(
                200, json_data={"id": "789", "fields": {}}
            )
            result = await client.list_item_return("site-123", "list-456", "789")
            mock_req.assert_called_once()
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "GET"
            assert call_kwargs["url"] == f"{BASE}site-123/lists/list-456/items/789"
            assert result == {"id": "789", "fields": {}}


class TestListItemCreate:
    """
    Test cases for the list item create method.
    """

    @pytest.mark.asyncio
    async def test_posts_correct_body(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(201, json_data={"id": "new-item"})
            result = await client.list_item_create(
                "site-123", "list-456", {"Title": "Hello"}
            )
            mock_req.assert_called_once()
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "POST"
            assert call_kwargs["url"] == f"{BASE}site-123/lists/list-456/items"
            assert call_kwargs["json"] == {"fields": {"Title": "Hello"}}
            assert result == {"id": "new-item"}


class TestListItemDelete:
    """
    Test cases for the list item delete method.
    """

    @pytest.mark.asyncio
    async def test_sends_delete(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(204)
            await client.list_item_delete("site-123", "list-456", "789")
            mock_req.assert_called_once()
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "DELETE"
            assert call_kwargs["url"] == f"{BASE}site-123/lists/list-456/items/789"


class TestListItemUpdate:
    """
    Test cases for the list item update method.
    """

    @pytest.mark.asyncio
    async def test_sends_patch_with_fields(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200)
            await client.list_item_update(
                "site-123", "list-456", "789", {"Title": "Updated"}
            )
            mock_req.assert_called_once()
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "PATCH"
            assert (
                call_kwargs["url"] == f"{BASE}site-123/lists/list-456/items/789/fields"
            )
            assert call_kwargs["json"] == {"Title": "Updated"}


class TestListItemAttachmentsReturn:
    """
    Test cases for the list item attachments return method.
    """

    @pytest.mark.asyncio
    async def test_info_only(self, client: GrafapClient) -> None:
        client._sp_token = "sp-tok"
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(
                200,
                json_data={
                    "d": {
                        "AttachmentFiles": {
                            "results": [
                                {
                                    "FileName": "doc.pdf",
                                    "ServerRelativeUrl": "/sites/MySite/doc.pdf",
                                }
                            ]
                        }
                    }
                },
            )
            result = await client.list_item_attachments_return(
                "https://contoso.sharepoint.com/sites/MySite",
                "MyList",
                42,
                download=False,
            )
            assert result == [{"name": "doc.pdf", "url": "/sites/MySite/doc.pdf"}]

    @pytest.mark.asyncio
    async def test_download(self, client: GrafapClient) -> None:
        client._sp_token = "sp-tok"
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            # First call: list attachments, second call: download file
            mock_req.side_effect = [
                _mock_response(
                    200,
                    json_data={
                        "d": {
                            "AttachmentFiles": {
                                "results": [
                                    {
                                        "FileName": "doc.pdf",
                                        "ServerRelativeUrl": "/sites/MySite/doc.pdf",
                                    }
                                ]
                            }
                        }
                    },
                ),
                _mock_response(200, content=b"fake-pdf-content"),
            ]
            result = await client.list_item_attachments_return(
                "https://contoso.sharepoint.com/sites/MySite",
                "MyList",
                42,
                download=True,
            )
            assert len(result) == 1
            assert result[0]["name"] == "doc.pdf"
            assert result[0]["data"] == b"fake-pdf-content"


class TestAdUsersReturn:
    """
    Test cases for the ad_users_return method.
    """

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = []
            await client.ad_users_return()
            call_kwargs = mock_paginated.call_args.kwargs
            assert call_kwargs["url"] == "https://graph.microsoft.com/v1.0/users"

    @pytest.mark.asyncio
    async def test_with_query_params(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = []
            await client.ad_users_return(
                select="id,displayName",
                filter="startswith(displayName,'A')",
            )
            call_kwargs = mock_paginated.call_args.kwargs
            assert call_kwargs["params"]["$select"] == "id,displayName"
            assert call_kwargs["params"]["$filter"] == "startswith(displayName,'A')"


class TestSpUsersInfoReturn:
    """
    Test cases for the sp_users_info_return method.
    """

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = []
            await client.sp_users_info_return("site-123")
            call_args = mock_paginated.call_args[0]
            assert (
                call_args[0] == f"{BASE}site-123/lists('{USER_INFO_LIST_NAME}')/items"
            )


class TestSpUserInfoReturn:
    """
    Test cases for the sp_user_info_return method.
    """

    @pytest.mark.asyncio
    async def test_by_user_id(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(
                200, json_data={"id": 42, "fields": {}}
            )
            result = await client.sp_user_info_return("site-123", user_id="42")
            call_kwargs = mock_req.call_args.kwargs
            assert (
                call_kwargs["url"]
                == f"{BASE}site-123/lists('{USER_INFO_LIST_NAME}')/items/42"
            )
            assert result == {"id": 42, "fields": {}}

    @pytest.mark.asyncio
    async def test_by_email(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(
                200,
                json_data={"value": [{"id": 1, "fields": {"Email": "a@b.com"}}]},
            )
            result = await client.sp_user_info_return("site-123", email="a@b.com")
            call_kwargs = mock_req.call_args.kwargs
            assert "fields/UserName eq 'a@b.com'" in call_kwargs["url"]
            assert result == {"id": 1, "fields": {"Email": "a@b.com"}}

    @pytest.mark.asyncio
    async def test_user_not_found(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, json_data={"value": []})
            with pytest.raises(Exception, match="could not find user"):
                await client.sp_user_info_return("site-123", email="nope@b.com")


class TestSpUserEnsure:
    """
    Test cases for the sp_user_ensure method.
    """

    @pytest.mark.asyncio
    async def test_posts_correct_body(self, client: GrafapClient) -> None:
        client._sp_token = "sp-tok"
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, json_data={"d": {"Id": 1}})
            result = await client.sp_user_ensure(
                "https://contoso.sharepoint.com/sites/MySite",
                "user@example.com",
            )
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "POST"
            assert call_kwargs["token_type"] == "sp"
            assert call_kwargs["json"] == {"logonName": "user@example.com"}
            assert result == {"d": {"Id": 1}}


class TestDoclibsReturn:
    """
    Test cases for the doclibs_return method.
    """

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = []
            await client.doclibs_return("site-123")
            mock_paginated.assert_called_once_with(
                f"{BASE}site-123/drives", context="get document libraries"
            )


class TestDoclibItemsReturn:
    """
    Test cases for the doclib_items_return method.
    """

    @pytest.mark.asyncio
    async def test_root_children(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = []
            await client.doclib_items_return("site-123", "drive-1")
            call_args = mock_paginated.call_args[0]
            assert call_args[0] == f"{BASE}site-123/drives/drive-1/root/children"

    @pytest.mark.asyncio
    async def test_subfolder_children(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = []
            await client.doclib_items_return(
                "site-123", "drive-1", subfolder_id="folder-2"
            )
            call_args = mock_paginated.call_args[0]
            assert (
                call_args[0] == f"{BASE}site-123/drives/drive-1/items/folder-2/children"
            )


class TestDoclibFileReturn:
    """
    Test doclib file return.
    """

    @pytest.mark.asyncio
    async def test_downloads_file(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(
                200,
                content=b"hello world",
                headers={"Content-Disposition": 'attachment; filename="test.txt"'},
            )
            result = await client.doclib_file_return("site-123", "file-1")
            assert result["file_name"] == '"test.txt"'  # quotes preserved from header
            assert result["file_content"] == b"hello world"

    @pytest.mark.asyncio
    async def test_non_200_raises(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(404, content=b"Not Found")
            with pytest.raises(Exception, match="could not download file"):
                await client.doclib_file_return("site-123", "file-1")


class TestDoclibFileViaUrlReturn:
    """
    Test cases for the doclib_file_via_url_return method.
    """

    @pytest.mark.asyncio
    async def test_downloads_via_url(self, client: GrafapClient) -> None:
        client._sp_token = "sp-tok"
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, content=b"pdf-data")
            result = await client.doclib_file_via_url_return(
                "https://contoso.sharepoint.com/sites/MySite/Docs/report.pdf"
            )
            assert result["name"] == "report.pdf"
            assert result["data"] == b"pdf-data"
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["token_type"] == "sp"


class TestDoclibFolderCreate:
    """
    Test cases for the doclib_folder_create method.
    """

    @pytest.mark.asyncio
    async def test_creates_folder(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(
                201, json_data={"id": "new-folder", "name": "MyFolder"}
            )
            result = await client.doclib_folder_create("site-123", "MyFolder")
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "POST"
            assert call_kwargs["json"]["name"] == "MyFolder"
            assert call_kwargs["json"]["folder"] == {}
            assert call_kwargs["json"]["@microsoft.graph.conflictBehavior"] == "fail"
            assert result == {"id": "new-folder", "name": "MyFolder"}

    @pytest.mark.asyncio
    async def test_non_201_raises(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(409, content=b"Conflict")
            with pytest.raises(Exception, match="could not create folder"):
                await client.doclib_folder_create("site-123", "MyFolder")


class TestDoclibFileCreate:
    """
    Test cases for the doclib_file_create method.
    """

    @pytest.mark.asyncio
    async def test_uploads_file(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(
                201, json_data={"id": "uploaded-file"}
            )
            result = await client.doclib_file_create(
                "site-123", "report.pdf", b"file-content", "application/pdf"
            )
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "PUT"
            assert call_kwargs["data"] == b"file-content"
            assert call_kwargs["headers"] == {"Content-Type": "application/pdf"}
            assert result == {"id": "uploaded-file"}

    @pytest.mark.asyncio
    async def test_non_2xx_raises(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(413, content=b"Too Large")
            with pytest.raises(Exception, match="could not upload file"):
                await client.doclib_file_create(
                    "site-123", "bad.txt", b"x" * 100, "text/plain"
                )


class TestDoclibFileDelete:
    """
    Test cases for the doclib_file_delete method.
    """

    @pytest.mark.asyncio
    async def test_deletes_file(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(204)
            await client.doclib_file_delete("site-123", "file-1")
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "DELETE"
            assert call_kwargs["url"] == f"{BASE}site-123/drive/items/file-1"

    @pytest.mark.asyncio
    async def test_non_204_raises(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(404, content=b"Not Found")
            with pytest.raises(Exception, match="could not delete file"):
                await client.doclib_file_delete("site-123", "file-1")


class TestTermstoreGroupsReturn:
    """
    Test cases for the termstore_groups_return method.
    """

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, json_data={"value": []})
            result = await client.termstore_groups_return("site-123")
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["method"] == "GET"
            assert call_kwargs["url"] == f"{BASE}site-123/termStore/groups"
            assert result == {"value": []}


# ---------------------------------------------------------------------------
# Sync proxy integration test
# ---------------------------------------------------------------------------


class TestSyncProxyIntegration:
    """
    Verify the sync proxy actually works end-to-end with mocked HTTP.
    """

    def test_sync_sites_return(self, client: GrafapClient) -> None:
        with patch.object(
            client, "_get_paginated", new_callable=AsyncMock
        ) as mock_paginated:
            mock_paginated.return_value = [{"id": "s1"}]
            result = client.sync.sites_return()
            assert result == [{"id": "s1"}]

    def test_sync_list_item_create(self, client: GrafapClient) -> None:
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(201, json_data={"id": "new-item"})
            result = client.sync.list_item_create(
                "site-123", "list-456", {"Title": "SyncTest"}
            )
            assert result == {"id": "new-item"}


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    """
    Test cases for the client close method.
    """

    @pytest.mark.asyncio
    async def test_close_cleans_up(self, client: GrafapClient) -> None:
        client._http_client = AsyncMock()
        await client.close()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_close_idempotent(self, client: GrafapClient) -> None:
        """
        Closing when no client exists should not error.
        """
        await client.close()  # should not raise
