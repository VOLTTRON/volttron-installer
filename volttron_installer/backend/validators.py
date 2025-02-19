import re

valid_field_name_for_conifg_pattern = re.compile(r"^[a-zA-Z_-][a-zA-Z0-9_-]*$")

def is_valid_field_name_for_config(field: str) -> bool:
    return valid_field_name_for_conifg_pattern.match(field) is not None

