"""
Test file for grafap.
"""

import os
import sys
from io import BytesIO

from dotenv import load_dotenv

# Load env vars from a .env file
load_dotenv()

sys.path.insert(0, "")

from grafap import doclib_file_create

# Create temp test.txt bytesio object for testing file upload
test_txt_file = BytesIO(b"This is a test file created by the grafap library.")

res = doclib_file_create(
    site_id=os.environ["SITE_ID_TESTING"],
    parent_id=os.environ["FOLDER_ID_TESTING"],
    file_name="test_file2.txt",
    file_content=test_txt_file.getvalue(),
    content_type="text/plain",
)

pass
