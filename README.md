# grafap

grafap (graph-wrap) is a Python package for interacting with the Microsoft Graph API, primarily sharepoint lists. Creating new items, querying lists, etc.

## Installation

`pip install grafap`

## Usage

Several environment variables are required for grafap to function. Most of the endpoints in grafap are just using the standard Microsoft Graph API which only requires a client ID and secret. The Sharepoint REST API, however requires using a client certificate. At least for the only endpoint being used thus far "ensure user".

*MS Graph Env Vars*

| Required? | Env Variable | Description |
| --------- | ------------ | ----------- |
| Yes | GRAPH_LOGIN_BASE_URL | Should be <https://login.microsoftonline.com/> |
| Yes | GRAPH_BASE_URL | Should be <https://graph.microsoft.com/v1.0/sites/> |
| Yes | GRAPH_TENANT_ID | Tenant ID from app registration created in Azure. |
| Yes | GRAPH_CLIENT_ID | Client ID from app registration created in Azure. |
| Yes | GRAPH_CLIENT_SECRET | Client secret from app registration created in Azure. |
| Yes | GRAPH_GRANT_TYPE | Should be 'client_credentials' |
| Yes | GRAPH_SCOPES | Should typically be <https://graph.microsoft.com/.default> unless using more fine-grained permissions. |

*Sharepoint Rest API Env Vars*

| Required? | Env Variable | Description |
| --------- | ------------ | ----------- |
| No | SP_SITE | Base Site URL you're interacting with. Should be <https://DOMAIN.sharepoint.com/> |
| No | SP_SCOPES | Scopes for sharepoint rest API. Should look like <https://{tenant name}.sharepoint.com/.default> |
| No | SP_LOGIN_BASE_URL | Should be <https://login.microsoftonline.com/> |
| No | SP_TENANT_ID | Tenant ID from app registration created in Azure. |
| No | SP_CLIENT_ID | Client ID from app registration created in Azure. |
| No | SP_GRANT_TYPE | client_credentials |
| No | SP_CERTIFICATE_PATH | Path to `.pfx` file |
| No | SP_CERTIFICATE_PASSWORD | Password for the `.pfx` file. |

### Sites

#### Get SharePoint Sites

Gets all SharePoint sites in the tenant.

### Lists

#### Get SharePoint Lists

Gets all SharePoint lists in a site. Takes one parameter:

*site_id* - ID for the given site.

#### Get SharePoint List Items

Gets all items in a sharepoint list. Takes 2 required parameters and 1 optional.

*site_id* - ID for which site list is in
*list_id* - ID for the list being queried
*filter_query* - Optional OData filter query, e.g. "Department eq 1234"

> Note: If you're using the filter_query expression, whichever field you want to filter on needs to be indexed or you'll get an error. To index a column, just add it in the sharepoint list settings.

#### Create SharePoint List Item

Creates a new item in a given sharepoint list. Takes three parameters:

*site_id* - long string with three components separated by commas. Starts with SP site URL (DOMAIN.sharepoint.com)
*list_id* - Unique ID for the given list you want to add an item to. Use the get_sp_lists function to get the IDs for all lists in a site.
*field_data* - Dictionary of fields you are populating. Formatted like below.

```json
{
    "FieldName": "FieldValue",
    "Field2Name": true
}
```

#### Update SharePoint List Item

Updates one or more fields of a particular item in a list. Formatted almost identically to create item function, but only including fields whose values are being updated, as well as additional item ID parameter. Takes four parameters:

*site_id* - long string with three components separated by commas. Starts with SP site URL (DOMAIN.sharepoint.com)
*list_id* - Unique ID for the given list you want to update item on. Use the get_sp_lists function to get the IDs for all lists in a site.
*item_id* - ID of the list item being updated
*field_data* - Dictionary of fields you are updating. Formatted like below.

```json
{
    "FieldName": "FieldValue",
    "Field2Name": true
}
```

### OneNote

Not yet implemented.

### Term Store

#### Get Termstore Groups

Lists all termstore group objects in a site

*site_id* - ID for which site list is in, can be 'root'

### Users

#### Get Users

Returns list of Azure AD users.

#### Get all SharePoint User's Info

Queries hidden User Information List. Returns info for all users in a site.

*site_id* - ID for which site list is in, can be 'root'

#### Get a Sharepoint User's Info

Queries hidden User Information List. Returns info for a specific user ID.

*site_id* - ID for which site list is in, can be 'root'
*user_id* - ID of the list item being queried

#### Ensure SharePoint User

"Ensures" a user for a given sharepoint site. Sharepoint doesn't, by default, have all users in a sharepoint tenant in each site you have. They have to interact with it in some way or you need to pick them on a Person field. So there's no way to programmatically set a user if they aren't already in the hidden Sharepoint User Information List in the site. Ensuring a user is essentially doing that, putting them in the list. The endpoint is not available in the MS Graph API, because Microsoft. So we need to use the SharePoint REST API for this.

*site_url* - Base URL of the sharepoint site
*logon_name* - Email of the user you want to ensure

### Get all Sharepoint Users' Info

Queries hidden User Information List SP list. Returns all user info so can be associated with lookup values.

*site_id* - ID for which site list is in, can be 'root'
