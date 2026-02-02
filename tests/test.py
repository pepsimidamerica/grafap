import os
import sys
from datetime import datetime, timedelta
from pprint import pprint

from dotenv import load_dotenv

# Load env vars from a .env file
load_dotenv()

sys.path.insert(0, "")

from grafap import doclibs_return

res = doclibs_return(site_id=os.environ["SITE_ID_MAIN"])

pass
