import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, "")

from grafap import *

res = grafap.ensure_sp_user(
    "SITE URL",
    "email@domain.com",
)

pass
