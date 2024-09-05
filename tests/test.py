import os
import sys
from datetime import datetime, timedelta
from pprint import pprint

from dotenv import load_dotenv

# Load env vars from a .env file
load_dotenv()

sys.path.insert(0, "")

from grafap import *

# SharePoint Sites

sites = grafap.get_sp_sites()

# SharePoint Lists

lists = grafap.get_sp_lists(sites[0]["id"])
list_items = grafap.get_sp_list_items(sites[0]["id"], lists[0]["id"])
list_item = grafap.get_sp_list_item(sites[0]["id"], lists[0]["id"], list_items[0]["id"])

grafap.create_sp_item(
    sites[0]["id"],
    lists[0]["id"],
    {
        "Title": "Test",
        "Description": "Test",
    },
)

grafap.update_sp_item(
    sites[0]["id"],
    lists[0]["id"],
    list_items[0]["id"],
    {
        "Title": "Test",
        "Description": "Test",
    },
)

grafap.delete_sp_item(sites[0]["id"], lists[0]["id"], list_items[0]["id"])

# SharePoint Site Users

res = grafap.ensure_sp_user(
    "SITE URL",
    "email@domain.com",
)

# List Attachments

attachments = get_list_attachments(
    os.environ["SP_SITE_INTERNAL"],
    os.environ["SP_SITE_EXAMPLE_LIST_NAME"],
    4,
    download=True,
)

# Write first attachment data to a file
with open(attachments[0]["name"], "wb") as f:
    f.write(attachments[0]["data"])
