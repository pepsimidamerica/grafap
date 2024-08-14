import os

import requests

from grafap.auth import Decorators


@Decorators.refresh_graph_token
def get_sp_sites() -> dict:
    """
    Gets all site data in a given tenant
    """
    if "GRAPH_BASE_URL" not in os.environ:
        raise Exception("Error, could not find GRAPH_BASE_URL in env")

    def recurs_get(url, headers):
        """
        Recursive function to handle pagination
        """
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(
                f"Error {response.status_code}, could not get sharepoint site data: ",
                response.content,
            )
            raise Exception(
                f"Error {response.status_code}, could not get sharepoint site data: "
                + str(response.content)
            )

        data = response.json()

        # Check for the next page
        if "@odata.nextLink" in data:
            return data["value"] + recurs_get(data["@odata.nextLink"], headers)
        else:
            return data["value"]

    result = recurs_get(
        os.environ["GRAPH_BASE_URL"],
        headers={"Authorization": "Bearer " + os.environ["GRAPH_BEARER_TOKEN"]},
    )
    return result
