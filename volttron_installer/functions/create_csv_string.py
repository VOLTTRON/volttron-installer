import csv
import io 

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