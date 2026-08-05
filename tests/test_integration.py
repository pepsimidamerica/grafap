"""
Integration / smoke tests that reach out to the real Microsoft Graph API.

These tests are skipped by default and only run when
explicitly selected with pytest -m integration.  They require valid
credentials in a `.env` file at the project root.

All tests only hit read-only endpoints. Just selecting.
"""

import os

import pytest
from grafap._client import GrafapClient

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_env(*keys: str) -> None:
    """
    Skip the current test if any required env var is missing.
    """
    missing = [k for k in keys if k not in os.environ]
    if missing:
        pytest.skip(f"Integration test requires env vars: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def live_client() -> GrafapClient:
    """
    Create a real GrafapClient from environment variables.

    Function-scoped so each test gets a fresh httpx.AsyncClient bound
    to the current event loop.  Token caching within the client instance
    still avoids redundant token requests within a single test.
    """
    _require_env(
        "GRAPH_TENANT_ID",
        "GRAPH_CLIENT_ID",
        "GRAPH_CLIENT_SECRET",
    )
    return GrafapClient.from_env()


# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------


class TestTokenAcquisition:
    """
    Verify that tokens can actually be acquired from Azure AD.
    """

    @pytest.mark.asyncio
    async def test_graph_token_acquired(self, live_client: GrafapClient) -> None:
        """
        _ensure_graph_token should fetch and cache a real token.
        """
        token = await live_client._ensure_graph_token()
        assert token is not None
        assert len(token) > 0
        # Token should be a JWT (three dot-separated segments)
        assert token.count(".") == 2

    @pytest.mark.asyncio
    async def test_graph_token_cached(self, live_client: GrafapClient) -> None:
        """
        Second call should return the cached token without a new request.
        """
        token1 = await live_client._ensure_graph_token()
        token2 = await live_client._ensure_graph_token()
        assert token1 == token2


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------


class TestSitesReturnLive:
    """
    Read-only smoke tests for sites_return().
    """

    @pytest.mark.asyncio
    async def test_returns_list(self, live_client: GrafapClient) -> None:
        sites = await live_client.sites_return()
        assert isinstance(sites, list)
        assert len(sites) > 0, "Expected at least one site in the tenant"

    @pytest.mark.asyncio
    async def test_site_has_expected_keys(self, live_client: GrafapClient) -> None:
        sites = await live_client.sites_return()
        site = sites[0]
        # Every site resource should have at least id and displayName
        assert "id" in site, f"Site missing 'id': {site}"
        assert "displayName" in site, f"Site missing 'displayName': {site}"


# ---------------------------------------------------------------------------
# Lists (requires a known site ID)
# ---------------------------------------------------------------------------


class TestListsReturnLive:
    """
    Read-only smoke tests for lists_return().
    """

    @pytest.mark.asyncio
    async def test_returns_lists_for_known_site(
        self, live_client: GrafapClient
    ) -> None:
        _require_env("SITE_ID_INTERNAL_ACCESS")
        site_id = os.environ["SITE_ID_INTERNAL_ACCESS"]

        lists = await live_client.lists_return(site_id)
        assert isinstance(lists, list)
        # A typical SharePoint site has at least a few built-in lists
        assert len(lists) > 0, f"Expected at least one list in site {site_id}"

    @pytest.mark.asyncio
    async def test_list_has_expected_keys(self, live_client: GrafapClient) -> None:
        _require_env("SITE_ID_INTERNAL_ACCESS")
        site_id = os.environ["SITE_ID_INTERNAL_ACCESS"]

        lists = await live_client.lists_return(site_id)
        lst = lists[0]
        assert "id" in lst, f"List missing 'id': {lst}"
        assert "displayName" in lst, f"List missing 'displayName': {lst}"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class TestAdUsersReturnLive:
    """
    Read-only smoke tests for ad_users_return().
    """

    @pytest.mark.asyncio
    async def test_returns_users(self, live_client: GrafapClient) -> None:
        users = await live_client.ad_users_return(select="id,displayName")
        assert isinstance(users, list)
        assert len(users) > 0, "Expected at least one user in the tenant"

    @pytest.mark.asyncio
    async def test_user_has_expected_keys(self, live_client: GrafapClient) -> None:
        users = await live_client.ad_users_return(select="id,displayName")
        user = users[0]
        assert "id" in user, f"User missing 'id': {user}"
        assert "displayName" in user, f"User missing 'displayName': {user}"

    @pytest.mark.asyncio
    async def test_select_limits_fields(self, live_client: GrafapClient) -> None:
        """When $select is used, only requested fields should be present."""
        users = await live_client.ad_users_return(select="id,displayName")
        user = users[0]
        # userPrincipalName should NOT be present since we didn't select it
        assert "userPrincipalName" not in user, (
            "Expected 'userPrincipalName' to be absent with select=id,displayName"
        )


class TestSpUsersInfoReturnLive:
    """
    Read-only smoke tests for sp_users_info_return().
    """

    @pytest.mark.asyncio
    async def test_returns_users_for_known_site(
        self, live_client: GrafapClient
    ) -> None:
        _require_env("SITE_ID_INTERNAL_ACCESS")
        site_id = os.environ["SITE_ID_INTERNAL_ACCESS"]

        users = await live_client.sp_users_info_return(site_id)
        assert isinstance(users, list)
        assert len(users) > 0, f"Expected at least one user in site {site_id}"


# ---------------------------------------------------------------------------
# Sync proxy (end-to-end with real API)
# ---------------------------------------------------------------------------


class TestSyncProxyLive:
    """
    erify the sync proxy works against the real API.
    """

    def test_sync_sites_return(self, live_client: GrafapClient) -> None:
        sites = live_client.sync.sites_return()
        assert isinstance(sites, list)
        assert len(sites) > 0
