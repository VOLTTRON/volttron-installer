import json, re, csv, io, yaml, os
from loguru import logger

def check_path(path):
    # Check if path contains invalid characters for the current OS
    try:
        # Normalize path to catch issues
        normalized_path = os.path.normpath(path)
        
        # Check for common invalid path characters
        # This handles most OS restrictions
        invalid_chars_pattern = re.compile(r'[:*?"<>|]')  # Common invalid chars in Windows
        if invalid_chars_pattern.search(normalized_path):
            return False
            
        # Check path isn't empty after normalization
        if not normalized_path or normalized_path.isspace():
            return False
            
        return True
    except:
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