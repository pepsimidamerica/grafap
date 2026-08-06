"""
Manual tests for grafap.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env")

from grafap._client import GrafapClient

client = GrafapClient.from_env()


async def test_get_file():
    res = await client.doclib_file_via_url_return(os.environ["TEST_FILE_URL"])
    return res


if __name__ == "__main__":
    import asyncio

    # Testing running async and sync methods
    async_file = asyncio.run(test_get_file())
    sync_file = client.sync.doclib_file_via_url_return(os.environ["TEST_FILE_URL"])
    sites = client.sync.sites_return()

    # Save the files
    with Path("async_output.pdf").open("wb") as f:
        f.write(async_file["data"])
    with Path("sync_output.pdf").open("wb") as f:
        f.write(sync_file["data"])
    with Path("sites.json").open("w") as f:
        f.write(json.dumps(sites))

    # Close the client
    asyncio.run(client.close())
