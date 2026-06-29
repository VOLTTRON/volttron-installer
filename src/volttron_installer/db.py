import json
import os
import glob

DB_DIR = 'instances_data'

def get_instances():
    if not os.path.exists(DB_DIR):
        return []
    instances = []
    for filepath in glob.glob(os.path.join(DB_DIR, '*.json')):
        try:
            with open(filepath, 'r') as f:
                instances.append(json.load(f))
        except Exception:
            pass
    return instances

def save_instance(instance):
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    filename = f"{instance.get('name', 'unknown')}.json"
    filepath = os.path.join(DB_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(instance, f, indent=4)

def delete_instance(instance_name):
    filepath = os.path.join(DB_DIR, f"{instance_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
