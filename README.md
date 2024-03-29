# grafap

grafap (graph-wrap) is a Python package for interacting with the Microsoft Graph API, primarily sharepoint lists. Creating new items, querying lists, etc.

## Installation

## Usage

Several environment variables are required for grafap to function.

> Note: The SP (SharePoint) environment variables are only needed if using the Get Site User By Lookup ID function since it uses a separate API that is for some godforsaken reason not available through Microsoft Graph. Even though Microsoft constantly shoves Graph down your throat and how cool and awesome it is.

| Required? | Env Variable | Description |
| --------- | ------------ | ----------- |
| Yes | GRAPH_LOGIN_BASE_URL |  |
| Yes | GRAPH_TENANT_ID |  |
| Yes | GRAPH_CLIENT_ID |  |
| Yes | GRAPH_CLIENT_SECRET |  |
| Yes | GRAPH_GRANT_TYPE | Should be client_credentials |
| Yes | GRAPH_SCOPES | Should typically be <https://graph.microsoft.com/.default> unless using more fine-grained permissions. |
| No | SP_LOGIN_BASE_URL | Should be same as graph login URL, just including as separate in case. |
| No | SP_TENANT_ID |  |
| No | SP_CLIENT_ID |  |
| No | SP_CLIENT_SECRET |  |
| No | SP_GRANT_TYPE |  |
| No | SP_SITE |  |

### Get SharePoint Sites

### Get SharePoint Lists

### Get SharePoint List Items

### Create SharePoint List Item

### Update SharePoint List Item

### Get Site User By Lookup ID

> Note: Uses SharePoint REST API, not the main Microsoft Graph API.
