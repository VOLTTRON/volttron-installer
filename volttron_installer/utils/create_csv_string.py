import csv
import io
from .validate_content import check_csv

def create_string_from_dict(data: dict[str: list[str]]) -> str:
    headers = list(data.keys())
    rows = []
    # Find the maximum length of the lists in the dictionary
    max_length = max(len(lst) for lst in data.values())
    # Iterate through the range of the maximum length
    for i in range(max_length):
        # Create a row with the values from each list, using an empty string if the list is shorter
        row = [data[key][i] if i < len(data[key]) else "" for key in headers]
        rows.append(row)
    return create_csv_string(headers, rows)

def create_csv_string(headers: list[str], rows: list[list[str]]) -> str:
    # Create an in-memory string buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(headers)

    # Write the data rows
    writer.writerows(rows)

    # Get the CSV string from the buffer
    csv_string = output.getvalue()
    output.close()

    return csv_string



def create_and_validate_csv_string(
    headers=None, 
    rows=None, 
    data_dict=None
) -> tuple[bool, str]:
    """
    Creates and validates a CSV string from either headers/rows or a dictionary.
    Ensures:
    1. All columns have the same number of filled entries
    2. No column is completely empty
    3. Empty rows at the end are omitted
    
    Args:
        headers: List of column headers (used if rows is provided)
        rows: List of rows where each row is a list of string values
        data_dict: Dictionary mapping column names to lists of values
        
    Returns:
        A tuple containing:
        - Boolean indicating if the CSV is valid
        - The CSV string (empty string if invalid when using data_dict)
    """
    # Handle input from dictionary if provided
    if data_dict is not None:
        headers = list(data_dict.keys())
        
        # First, determine how many non-empty entries are in each column
        non_empty_counts = {}
        for key, values in data_dict.items():
            # Count non-empty strings in this column
            count = sum(1 for v in values if v.strip() != "")
            non_empty_counts[key] = count
            
            # Check for completely empty columns
            if count == 0:
                # Found a completely empty column
                return False, ""
        
        # Check if all columns have the same number of filled entries
        counts = list(non_empty_counts.values())
        if len(counts) > 1 and len(set(counts)) > 1:
            # Columns have different numbers of filled entries
            return False, ""
        
        # Find the maximum row with content
        max_non_empty_row = -1
        for key, values in data_dict.items():
            for i, v in enumerate(values):
                if v.strip():
                    max_non_empty_row = max(max_non_empty_row, i)
        
        # Only include rows up to the last non-empty row
        rows = []
        for i in range(max_non_empty_row + 1):
            row = [data_dict[key][i] if i < len(data_dict[key]) else "" for key in headers]
            rows.append(row)
    
    # Check for empty columns in row format
    elif rows is not None and headers is not None:
        # First, trim empty rows at the end
        last_non_empty_idx = -1
        for i, row in enumerate(rows):
            if any(cell.strip() for cell in row):
                last_non_empty_idx = i
        
        # Only keep rows up to the last non-empty one
        rows = rows[:last_non_empty_idx + 1]
        
        # Now check for empty columns
        columns = list(zip(*rows)) if rows else []
        
        # Check if any column is completely empty
        for i, column in enumerate(columns):
            if all(cell.strip() == "" for cell in column):
                return False, ""
        
        # Check if all columns have the same number of non-empty entries
        non_empty_counts = []
        for column in columns:
            count = sum(1 for cell in column if cell.strip() != "")
            non_empty_counts.append(count)
        
        if len(non_empty_counts) > 1 and len(set(non_empty_counts)) > 1:
            return False, ""
    
    # Create CSV string
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows) if rows else None
    
    csv_string = output.getvalue()
    output.close()
    
    # Check if the CSV is valid
    is_valid = check_csv(csv_string)
    
    return is_valid, csv_string