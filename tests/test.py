import os
import sys
from datetime import datetime, timedelta
from pprint import pprint

from dotenv import load_dotenv

# Load env vars from a .env file
load_dotenv()

sys.path.insert(0, "")

from grafap import doclib_items_return, doclibs_return

res = doclibs_return(site_id=os.environ["SITE_ID_MAIN"])

doclib_id = res[0]["id"]

res2 = doclib_items_return(
    site_id=os.environ["SITE_ID_MAIN"],
    doclib_id=doclib_id,
    subfolder_id=os.environ["SUBFOLDER_ID"],
)

pass
