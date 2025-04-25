import json, re, csv, io, yaml, os
from loguru import logger
from pathlib import Path

def check_path(path_str: str) -> bool:
    if not isinstance(path_str, str) or not path_str:
        return False
    
    # Try to normalize the path (handles ~, ., .. etc.)
    try:
        # Expand user directory if present (~/...)
        if '~' in path_str:
            path_str = os.path.expanduser(path_str)
            
        # Try to get the absolute path - this will fail for many invalid paths
        path_str = os.path.normpath(path_str)
        
        # On Windows, additional validation for reserved names like COM1, LPT1, etc.
        if os.name == 'nt':
            drive, path = os.path.splitdrive(path_str)
            if drive and path and re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', 
                                          path.lstrip('\\').split('\\')[0], 
                                          re.IGNORECASE):
                return False
        
        # Additional check: try creating a Path object
        Path(path_str)
        
        # Check for invalid characters based on OS
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*'] if os.name == 'nt' else ['\0']
        if any(char in path_str for char in invalid_chars):
            return False
            
        return True
        
    except (ValueError, TypeError, AttributeError):
        return False

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

def check_yaml(yaml_string: str) -> bool:
    yaml_string = yaml_string.strip()

    try:
        yaml.safe_load(yaml_string)
        return True
    except yaml.YAMLError:
        return False

def check_csv(csv_string: str) -> bool:
    try:
        # Parse the CSV string
        input = io.StringIO(csv_string)
        reader = csv.reader(input)
        
        headers = next(reader)  # Read the headers
        num_columns = len(headers)
        
        # Check each row for the correct number of columns
        for row in reader:
            if len(row) != num_columns:
                logger.debug(f"Row length mismatch: expected {num_columns}, got {len(row)}")
                return False

        return True

    except Exception as e:
        logger.debug(f"CSV verification error: {e}")
        return False
    
def check_regular_expression(regex_string: str) -> bool:
    valid_field_name_for_config_pattern = re.compile(r"^[a-zA-Z_-][a-zA-Z0-9_.-]*$")
    return valid_field_name_for_config_pattern.match(regex_string) is not None