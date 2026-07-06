import json
import os
import glob

# Resolve the installer data directory once at import time, using an absolute
# path that does NOT float with the process cwd.  The env-var override still
# works; the fallback is a stable home-relative directory.
_DATA_DIR_BASE = os.environ.get(
    'VOLTTRON_INSTALLER_DATA_DIR',
    os.path.join(os.path.expanduser('~'), '.volttron_installer_data'),
)
DB_DIR = os.path.join(_DATA_DIR_BASE, 'instances_data')

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
