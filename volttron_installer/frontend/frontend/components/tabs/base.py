import reflex as rx
import typing

BASE_TYPE_ANNOTATION = typing.Dict[str, typing.Dict[str, typing.Any]]

BASE_HOST_TEMPLATE_DATA: BASE_TYPE_ANNOTATION =  {
                    "host_id": "",
                    "ssh_sudo_user": "",
                    "identity_file": "~/.ssh/id_rsa",
                    "ssh_ip_address": "",
                    "ssh_port": ""
                    }

BASE_CONFIG_TEMPLATE_DATA: BASE_TYPE_ANNOTATION = {
    "config_name" : "",
    "config_type" : "JSON",
    "config" : '{\n"driver_config": {"device_address": "10.0.0.1",\n        "device_id": 500\n    },\n    "driver_type": "bacnet",\n    "registry_config":"config://bacnet.csv",\n    "interval": 10,\n    "timezone": "UTC"\n}'
}

BASE_AGENT_DATA: BASE_TYPE_ANNOTATION = {
    "agent_name" : "",
    "vip_identity" : "",
    "identity_file" : "",
    "agent_config_store" : {
        # "" : {
        #     "config_type": "JSON",
        #     "config" : ""
        # }
    }
}

BASE_PLATFORM_DATA: BASE_TYPE_ANNOTATION = {
    "name" : "",
    "address" : "",
    "bus_type" : "ZMQ",
    "ports" : "",
    "deployed" : "",
    "running" : "",
    "host" : {
        },
    "agents" : {
        "agent_name" : {
        
        }
    }
}

"""
```python
# Example:

platform = {
    "platform_uid" : {
        "name" : str,
        "address" : str,
        "bus_type" : "ZMQ",
        "ports" : str,
        "deployed" : bool,
        "running" : bool
        "host" : {
            ... # base host data
        },
        "agents" : {
            # optional but would look like:
            "agent_name" : {
                ... # base agent data
            }
        }
    }
}
```
"""
