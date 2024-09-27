# # @Decorators.refresh_graph_token_delegated
# def get_user_notebooks():
#     """
#     Gets all notebooks for the signed-in user
#     """
#     if "GRAPH_BASE_URL" not in os.environ:
#         raise Exception("Error, could not find GRAPH_BASE_URL in env")

#     response = requests.get(
#         os.environ["GRAPH_BASE_URL"] + "me/onenote/notebooks",
#         headers={
#             "Authorization": "Bearer " + os.environ["USER_BEARER_TOKEN"],
#             "Accept": "application/json",
#         },
#         timeout=30,
#     )

#     if response.status_code != 200:
#         raise Exception("Error, could not get user notebooks: " + str(response.content))

#     return response.json()


# # @Decorators.refresh_graph_token_delegated
# def get_notebook_sections(notebook_id: str):
#     """
#     Gets all sections in a notebook
#     """
#     if "GRAPH_BASE_URL" not in os.environ:
#         raise Exception("Error, could not find GRAPH_BASE_URL in env")

#     response = requests.get(
#         os.environ["GRAPH_BASE_URL"]
#         + "me/onenote/notebooks/"
#         + notebook_id
#         + "/sections",
#         headers={
#             "Authorization": "Bearer " + os.environ["USER_BEARER_TOKEN"],
#             "Accept": "application/json",
#         },
#         timeout=30,
#     )

#     if response.status_code != 200:
#         raise Exception(
#             "Error, could not get notebook sections: " + str(response.content)
#         )

#     return response.json()


# # @Decorators.refresh_graph_token_delegated
# def get_section_pages(notebook_id: str, section_id: str):
#     """
#     Gets all pages in a section
#     """
#     if "GRAPH_BASE_URL" not in os.environ:
#         raise Exception("Error, could not find GRAPH_BASE_URL in env")

#     response = requests.get(
#         os.environ["GRAPH_BASE_URL"]
#         + "me/onenote/notebooks/"
#         + notebook_id
#         + "/sections/"
#         + section_id
#         + "/pages",
#         headers={
#             "Authorization": "Bearer " + os.environ["USER_BEARER_TOKEN"],
#             "Accept": "application/json",
#         },
#         timeout=30,
#     )

#     if response.status_code != 200:
#         raise Exception("Error, could not get section pages: " + str(response.content))

#     return response.json()
