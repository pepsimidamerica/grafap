import os

import requests

from grafap.auth import Decorators


@Decorators.refresh_graph_token
def get_sp_termstore_groups(site_id: str) -> dict:
    """
    Lists all termstore group objects in a site

    :param site_id: The site id
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    response = requests.get(
        os.environ["GRAPH_BASE_URL"] + site_id + "/termStore/groups",
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
        timeout=30,
    )

    if response.status_code != 200:
        print(
            f"Error {response.status_code}, could not get termstore groups: ",
            response.content,
        )
        raise Exception(
            f"Error {response.status_code}, could not get termstore groups: "
            + str(response.content)
        )

    return response.json()
