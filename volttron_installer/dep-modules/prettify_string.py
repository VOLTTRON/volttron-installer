import json
import yaml

def prettify_json(data):
    if not data:
        return data
    
    if isinstance(data, dict):
        # If the data is already a dictionary, just pretty # print it
        return json.dumps(data, indent=4)

    # Assuming the input is a string; normalize single to double quotes for JSON compatibility
    data = data.replace("'", '"')
    
    try:
        # Try parsing the string as JSON
        parsed_json_data = json.loads(data)
        pretty_json_data = json.dumps(parsed_json_data, indent=4)
        # print("Hello im prettify json and this is the type im returning", type(pretty_json_data))
        # print(f"and this is my compy output:\n{pretty_json_data}")
        return pretty_json_data
    except json.JSONDecodeError:
        # print("Error occurred parsing supposed JSON string:", data)
        return data
    
def prettify_yaml(yaml_data: str) -> str:
    """
    Prettifies YAML data.

    :param yaml_data: The YAML data to prettify (either as a dict or a YAML string).
    :return: A prettified YAML string.
    """

    # If yaml_data is a dictionary, convert it to a YAML string
    if isinstance(yaml_data, dict):
        yaml_data = yaml.dump(yaml_data, sort_keys=False, default_flow_style=False)
    
    try:
        # Load the YAML data to handle any formatting errors
        data = yaml.safe_load(yaml_data)
        
        # Convert back to a prettified YAML string
        prettified_yaml = yaml.dump(data, sort_keys=False, default_flow_style=False)
        # print("\nThis is the YAML I'm prettifying:\n", prettified_yaml)
        return prettified_yaml
    except yaml.YAMLError as exc:
        # print(f"Error in YAML formatting: {exc}")
        return yaml_data