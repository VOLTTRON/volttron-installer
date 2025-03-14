import json
import re
from typing import Tuple

def prettify_json(json_string: str, indent: int = 4) -> Tuple[str, bool]:
    """
    Attempts to prettify a JSON string.
    
    Args:
        json_string: String to prettify
        indent: Number of spaces for indentation
        
    Returns:
        tuple: (prettified_string, success_flag)
               If successful, returns (prettified_json, True)
               If failed, returns (original_string, False)
    """
    if not json_string or not isinstance(json_string, str):
        return json_string, False
    
    # First try with the original string
    try:
        parsed = json.loads(json_string)
        return json.dumps(parsed, indent=indent), True
    except json.JSONDecodeError:
        # If that fails, try to fix common issues
        pass
    
    # Clean up the JSON string
    try:
        # Remove leading/trailing whitespace
        cleaned = json_string.strip()
        
        # Replace single quotes with double quotes
        cleaned = re.sub(r"(?<!\\)'", '"', cleaned)
        
        # Fix double quotes that might have been escaped incorrectly
        cleaned = re.sub(r'\\"', '"', cleaned)
        
        # Remove trailing commas in arrays and objects
        cleaned = re.sub(r',\s*]', ']', cleaned)
        cleaned = re.sub(r',\s*}', '}', cleaned)
        
        # Try to parse the cleaned JSON
        parsed = json.loads(cleaned)
        return json.dumps(parsed, indent=indent), True
    except json.JSONDecodeError:
        # If all attempts fail, return the original string
        return json_string, False