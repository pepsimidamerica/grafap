# grafap

grafap (graph-wrap) is a Python package for interacting with the Microsoft Graph API, primarily sharepoint lists. Creating new items, querying lists, etc.

## Installation

`pip install grafap`

## Usage

Several environment variables are required for grafap to function. Most of the endpoints in grafap are just using the standard Microsoft Graph API which only requires a client ID and secret.

The Sharepoint REST API, however requires using a client certificate. The Sharepoint REST API is currently only used for the following functions. If you're not using them, then you don't need the certificate or the other env vars in the Sharepoint REST API table. Only the vars in the Graph table.

- "ensuring" a user in a sharepoint site.
- downloading an attachment from a sharepoint list item

### MS Graph Env Vars

| Env Variable | Description |
| ------------ | ----------- |
| GRAPH_LOGIN_BASE_URL | Should be <https://login.microsoftonline.com/> |
| GRAPH_BASE_URL | Should be <https://graph.microsoft.com/v1.0/sites/> |
| GRAPH_TENANT_ID | Tenant ID from app registration created in Azure. |
| GRAPH_CLIENT_ID | Client ID from app registration created in Azure. |
| GRAPH_CLIENT_SECRET | Client secret from app registration created in Azure. |
| GRAPH_GRANT_TYPE | Should be 'client_credentials' |
| GRAPH_SCOPES | Should typically be <https://graph.microsoft.com/.default> unless using more fine-grained permissions. |

### Sharepoint Rest API Env Vars

| Env Variable | Description |
| ------------ | ----------- |
| SP_SITE | Base Site URL you're interacting with. Should be <https://DOMAIN.sharepoint.com/> |
| SP_SCOPES | Scopes for sharepoint rest API. Should look like <https://{tenant name}.sharepoint.com/.default> |
| SP_LOGIN_BASE_URL | Should be <https://login.microsoftonline.com/> |
| SP_TENANT_ID | Tenant ID from app registration created in Azure. |
| SP_CLIENT_ID | Client ID from app registration created in Azure. |
| SP_GRANT_TYPE | client_credentials |
| SP_CERTIFICATE_PATH | Path to `.pfx` file |
| SP_CERTIFICATE_PASSWORD | Password for the `.pfx` file. |

## Examples

A few examples of using grafap functions have been added in `tests/test.py`
