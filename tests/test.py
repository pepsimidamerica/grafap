"""
Test file for grafap.
"""

import sys

from dotenv import load_dotenv

# Load env vars from a .env file
load_dotenv()

sys.path.insert(0, "")

from grafap import doclib_file_via_url_return

res = doclib_file_via_url_return("TESTURLHERE")

pass
