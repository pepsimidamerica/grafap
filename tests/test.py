import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, "")

from grafap import *

sites = grafap.get_sp_sites()

pass
