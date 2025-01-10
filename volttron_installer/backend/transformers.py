def normalize_file_name(file_name: str) -> str:
    return file_name.replace(" ", "_").replace("-", "_").replace(".", "_").lower()
