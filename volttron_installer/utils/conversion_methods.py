import io, csv, json
from loguru import logger

def json_string_to_csv_string(json_string: str) -> str:
    # Clean JSON string
    json_string = json_string.replace("\n", "").replace(" ", "").replace("\r", "").replace("\ ", "")
    """Convert a JSON string back to a CSV string"""
    # Parse JSON string to Python data
    json_data = json.loads(json_string)
    
    if not json_data:
        return ""
    
    # Create a string buffer to write CSV data
    output = io.StringIO()
    
    # Handle both single objects and arrays of objects
    if isinstance(json_data, dict):
        # Convert single object to a list with one item
        json_data = [json_data]
    
    # Get field names from the first object
    fieldnames = json_data[0].keys()
    
    # Create CSV writer
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    
    # Write header and rows
    writer.writeheader()
    for row in json_data:
        writer.writerow(row)
    
    # Get the resulting CSV string
    csv_string = output.getvalue()
    output.close()
    
    return csv_string

def identify_string_format(mystery_string: str) -> str:
    # Try to parse the string as JSON
    try:
        json.loads(mystery_string)
        return "JSON"
    except json.JSONDecodeError:
        pass
    
    # Try to parse the string as CSV
    try:
        csv_file = io.StringIO(mystery_string)
        csv_reader = csv.reader(csv_file)
        # If it successfully reads the first row, it's likely a CSV
        if next(csv_reader, None) is not None:
            return "CSV"
    except csv.Error:
        pass
    
    # If neither parsing succeeds, return 'Unknown'
    return "Unknown"

def csv_string_to_json_string(csv_string) -> str:
    """Convert a CSV string to a JSON string"""
    # Use a string IO object to simulate a file
    csv_file = io.StringIO(csv_string)
    
    # Read CSV data
    reader = csv.DictReader(csv_file)
    
    # Convert to list of dictionaries
    result = [row for row in reader]
    
    # Convert to JSON string
    return json.dumps(result)

def csv_string_to_usable_dict(csv_string: str) -> dict[str, list[str]]:
    """
    Convert a CSV string to a dictionary with headers as keys and columns as lists of values.
    Each column will always contain at least 10 rows, padding with empty strings as needed.
    
    Args:
        csv_string: A string containing CSV data
        
    Returns:
        A dictionary where keys are the CSV headers and values are lists of cell values
        in that column, with at least 10 rows per column
    """
    # Handle empty or None input
    if not csv_string:
        return {}
    
    # Create a file-like object from the string
    csv_file = io.StringIO(csv_string)
    
    # Parse the CSV
    reader = csv.reader(csv_file)
    
    # Get the headers from the first row
    try:
        headers = next(reader)
    except StopIteration:
        # CSV is empty or has no rows
        return {}
    
    # Initialize the result dictionary with empty lists for each header
    result = {header: [] for header in headers}
    
    # Process each row and add values to the corresponding header list
    for row in reader:
        for i, value in enumerate(row):
            if i < len(headers):  # Ensure we don't go out of bounds
                result[headers[i]].append(value)
    
    # Ensure all columns have at least 10 rows by padding with empty strings
    for header in result:
        current_length = len(result[header])
        if current_length < 10:
            result[header].extend([""] * (10 - current_length))
    
    return result

def usable_dict_to_csv_string(working_dict: dict[str, list[str]]) -> str:
    return ''