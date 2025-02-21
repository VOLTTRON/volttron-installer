import re


def normalize_name_for_file(id: str) -> str:
    """Normalize the name for a file"""
    id = re.sub(r'[^a-zA-Z0-9-_]', '', id)
    return id.lower()