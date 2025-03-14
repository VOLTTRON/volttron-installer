import io, csv, json

def json_string_to_csv_string(json_string: str) -> str:
    # Clean JSON string
    json_string.replace("\n", "").replace(" ", "").replace("\r", "").replace("\ ", "")

    # Convert JSON string to a dictionary
    data = json.loads(json_string)
    
    # Check if data is a list of dictionaries or a single dictionary
    if isinstance(data, list):
        dict_list = data
    elif isinstance(data, dict):
        dict_list = [data]
    else:
        raise ValueError("JSON data must be a dictionary or a list of dictionaries")
    
    # Get the keys (column names) from the first dictionary
    keys = dict_list[0].keys()

    # Create in-memory file object for CSV
    csv_file = io.StringIO()
    csv_writer = csv.DictWriter(csv_file, fieldnames=keys)
    csv_writer.writeheader()
    csv_writer.writerows(dict_list)

    # Get CSV string from in-memory file object
    csv_file.seek(0)  # Reset pointer to the start of the file
    csv_string = csv_file.getvalue()
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
    # Convert CSV string to in-memory file object
    csv_file = io.StringIO(csv_string)
    csv_reader = csv.DictReader(csv_file)
    
    # Assuming the CSV contains only one row of data
    data = next(csv_reader)

    # Convert dictionary to JSON string
    json_string = json.dumps(data, indent=4)
    return json_string

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