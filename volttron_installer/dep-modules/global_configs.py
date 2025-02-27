"""
Example:

global agents: list[dict] = [
                    {       
                        'agent_name' : 'ListenerAgent' 
                        'agent_configuration' : {'key' : 'value'}, #JSON
                        'identity' : 'Listener',
                        'agent_path' : '/path/to/identity.file',
                        'config_entries' : ['config', 'config2']
                    }
                ]

An agent name houses all the things for an agent, these dictionaries are formed and appended
global agents once an agent is properly set up

NOTE:
When registering a platform under a host, the platform will execute their own function
appending themselves to the host, the function will have to grab the index of the host
using the `find_dict_index()` method, should look something like this:

global_hosts[index][platform_uid] = self

this will call the event listener in the platform which will tell all objects to update their ui
to the new change.

"""

from volttron_installer.modules.write_to_json import dump_to_var

# Establishing agents.json into global_agents
global_agents: dict = dump_to_var("agents")

# Establishing agents.json into global_hosts
global_hosts: dict = dump_to_var("hosts")

# Establishing drivers.json into global_drivers
global_drivers: dict = dump_to_var("drivers")

platforms: dict = dump_to_var("platforms")



def find_dict_index(lst: list[dict], name):
    """
    Finds the index of the dictionary containing the specified name in a list of dictionaries.
    The name must match the value of the first item in each dictionary as it is designed to hold
    the name (lst[x][0] will always = host_id/agent_name/name(drivers)).

    Args:
        lst: A list of dictionaries, where each dictionary represents an item.
        name: The name to search for.

    Returns:
        The index of the dictionary containing the specified name, or None if not found.
    """
    for index, item in enumerate(lst):
        first_key = next(iter(item))
        if item[first_key] == name:
            return index
    return None
