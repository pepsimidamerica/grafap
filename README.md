# grafap

grafap is a Python package for interacting with the Microsoft Graph API and the Sharepoint REST API. Primarily common functions with regards to sharepoint lists. Creating new items, querying lists, etc.

## Usage

```python
from grafap import GrafapClient

client = GrafapClient(
    tenant_id="...",
    client_id="...",
    client_secret="...",
)

# Or just use convenience func to pull from expected env vars
# if already loaded
client = GrafapClient.from_env()

# async
sites = await client.sites_return()

# sync
sites = client.sync.sites_return()
```

Can run untit tests with `uv run pytest tests -v` when in the project root. Integration tests require real Graph API credentials and network access, so they are marked with `@pytest.mark.integration` and can be run separately with `uv run pytest tests -v -m integration`.

## Configuration

Several parameters are required for grafap client instantiation. Most of the endpoints in grafap are just using the standard Microsoft Graph API which only requires a client ID and secret.

The Sharepoint REST API, however requires using a client certificate. The Sharepoint REST API is currently only used for the following functions (that don't have an equivalent in the Microsoft Graph API). If you're not using them, then you don't need the certificate or the other vars in the Sharepoint REST API table.

- "ensuring" a user in a sharepoint site.
- downloading an attachment from a sharepoint list item

### MS Graph Vars

| Env Variable | Description |
| ------------ | ----------- |
| GRAPH_LOGIN_BASE_URL | Should be <https://login.microsoftonline.com/> |
| GRAPH_BASE_URL | Should be <https://graph.microsoft.com/v1.0/sites/> |
| GRAPH_TENANT_ID | Tenant ID from app registration created in Azure. |
| GRAPH_CLIENT_ID | Client ID from app registration created in Azure. |
| GRAPH_CLIENT_SECRET | Client secret from app registration created in Azure. |
| GRAPH_GRANT_TYPE | Should be 'client_credentials' |
| GRAPH_SCOPES | Should typically be <https://graph.microsoft.com/.default> unless using more fine-grained permissions. |

### Sharepoint Rest API Vars

| Env Variable | Description |
| ------------ | ----------- |
| SP_SITE | Base Site URL you're interacting with. Should be <https://DOMAIN.sharepoint.com/> |
| SP_SCOPES | Scopes for sharepoint rest API. Should look like <https://{tenant name}.sharepoint.com/.default> |
| SP_LOGIN_BASE_URL | Should be <https://login.microsoftonline.com/> |
| SP_TENANT_ID | Tenant ID from app registration created in Azure. |
| SP_CLIENT_ID | Client ID from app registration created in Azure. |
| SP_GRANT_TYPE | client_credentials |
| SP_CERTIFICATE_PATH | Path to .pfx file |
| SP_CERTIFICATE_PASSWORD | Password for the .pfx file. |
