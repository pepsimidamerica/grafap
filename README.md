# grafap

grafap (graph-wrap) is a Python package for interacting with the Microsoft Graph API, primarily sharepoint lists. Creating new items, querying lists, etc.

## Installation

`pip install grafap`

## Usage

Several environment variables are required for grafap to function.

~~> Note: The SP (SharePoint) environment variables are only needed if using the Get Site User By Lookup ID function since it uses a separate API that is for some godforsaken reason not available through Microsoft Graph. Even though Microsoft constantly shoves Graph down your throat and how cool and awesome it is. They may be same values as the Graph variables if you've given access to both APIs to the same app.~~
Nevermind, they just decided it would be cool and fun to hide the user information list. You just have to know a guy to get into the club.

| Required? | Env Variable | Description |
| --------- | ------------ | ----------- |
| Yes | GRAPH_LOGIN_BASE_URL | Should be <https://login.microsoftonline.com/> |
| Yes | GRAPH_BASE_URL | Should be <https://graph.microsoft.com/v1.0/sites/> |
| Yes | GRAPH_TENANT_ID | Tenant ID from app registration created in Azure. |
| Yes | GRAPH_CLIENT_ID | Client ID from app registration created in Azure. |
| Yes | GRAPH_CLIENT_SECRET | Client secret from app registration created in Azure. |
| Yes | GRAPH_GRANT_TYPE | Should be 'client_credentials' |
| Yes | GRAPH_SCOPES | Should typically be <https://graph.microsoft.com/.default> unless using more fine-grained permissions. |
| No | SP_SITE | Base Site URL you're interacting with. Should be <https://DOMAIN.sharepoint.com/> |

### Get SharePoint Sites

Gets all SharePoint sites in the tenant.

### Get SharePoint Lists

Gets all SharePoint lists in a site. Takes one parameter:

*site_id* - ID for the given site.

### Get SharePoint List Items

Gets all items in a sharepoint list. Takes 2 required parameters and 1 optional.

*site_id* - ID for which site list is in
*list_id* - ID for the list being queried
*filter_query* - Optional OData filter query, e.g. "Department eq 1234"

> Note: If you're using the filter_query expression, whichever field you want to filter on needs to be indexed or you'll get an error. To index a column, just add it in the sharepoint list settings.

### Create SharePoint List Item

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

### Update SharePoint List Item

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

### Get all Sharepoint Users' Info

Queries hidden User Information List SP list. Returns all user info so can be associated with lookup values.

*site_id* - ID for which site list is in, can be 'root'

### Get a Sharepoint User's Info

Queries hidden User Information List. Returns info for a specific user ID.

*site_id* - ID for which site list is in, can be 'root'
*user_id* - ID of the list item being queried
