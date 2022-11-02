import pathlib

DEV_INST_IDS = [
    "1657225964-b1c9306d-4ec1-42ad-a1f0-d4a9fbace397",
    "1660066208-109a819c-95a0-432b-b1ba-bfe2a8987ccf",
]
DEV_DIRS = [pathlib.Path(f"data/{id_}/") for id_ in DEV_INST_IDS]
