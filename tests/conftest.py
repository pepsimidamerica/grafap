"""
Shared test fixtures for grafap.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from grafap._client import GrafapClient

# Load .env from project root so integration tests can pick up credentials.
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


@pytest.fixture
def client() -> GrafapClient:
    """
    Return a GrafapClient with fake credentials — no real network calls.
    """
    return GrafapClient(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        sp_certificate_path="fake-cert.pfx",
        sp_certificate_password="fake-password",
    )


@pytest.fixture
def client_no_sp() -> GrafapClient:
    """
    Return a GrafapClient without SharePoint REST credentials.
    """
    return GrafapClient(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Remove grafap-related env vars so from_env() tests start clean.
    """
    for key in list(os.environ):
        if key.startswith(("GRAPH_", "SP_")):
            monkeypatch.delenv(key, raising=False)
