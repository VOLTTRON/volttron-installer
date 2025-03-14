import json
import re

def check_json(json_string: str) -> bool:
    # Remove leading and trailing whitespace from the input string
    custom_json: str = json_string.strip()
    
    # Replace single quotes with double quotes
    custom_json = re.sub(r"'", '"', custom_json)
    
    # If the resulting string is empty, return False
    if not custom_json:
        return False
    
    # Try to load and dump the JSON to verify its validity
    try:
        loaded_json = json.loads(custom_json)
        dumped_json = json.dumps(loaded_json, indent=4)
        return True
    except json.JSONDecodeError:
        return False
