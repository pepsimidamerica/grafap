"""
Various constants used throughout the grafap package.
"""

# OData pagination
ODATA_NEXT_LINK = "@odata.nextLink"
ODATA_VALUE = "value"

# HTTP headers
SP_ODATA_VERBOSE = "application/json;odata=verbose;charset=utf-8"
GRAPH_PREFER_OPTIONAL = "HonorNonIndexedQueriesWarningMayFailRandomly"

# Timeouts (in seconds)
DEFAULT_TIMEOUT = 30
FILE_OPERATION_TIMEOUT = 60  # More time for file uploads/downloads

# Default sharepoint list names
USER_INFO_LIST_NAME = "User Information List"
