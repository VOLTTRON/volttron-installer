import json

def clean_json_string( json_string: str) -> str:
    try:
        # Attempt to parse
        decoded_string = json.loads(json_string)
        # Pretty # print to ensure it's well-formatted
        cleaned_string = json.dumps(decoded_string, indent=4)
        # print("\ndawg this is my cleaned string:\n", cleaned_string)
        return cleaned_string
    except json.JSONDecodeError as e:
        # # print error for debugging
        # print(f"JSON Decode Error: {e}")
        return json_string.strip()