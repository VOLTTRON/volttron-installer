import reflex as rx 
from .base import *

class Agents(rx.State): 
    committed_agents: dict[str, dict[str, str]] = {}
    agents:           dict[str, dict[str, str]] = committed_agents.copy()
    

    # Vars
    @rx.var(cache=True)
    def committed_agents_list(self) -> list[str]: return list(self.committed_agents.keys())

    # Events
    @rx.event
    def save_agent(self, agent_name: str):
        self.committed_agents[agent_name] = self.agents[agent_name]

    @rx.event
    def revert_agent(self, agent_name: str):
        self.agents[agent_name] = self.committed_agents[agent_name]
    
    @rx.event
    def handle_config_submit(self):
        print("we saved")

    @rx.event
    def update_form_field(self, agent_name: str, field: str, value: str):
        working_form: dict = self.agents[agent_name]
        working_form[field] = value

    @rx.event
    def remove_form(self, agent_name: str):
        # NOTE
        # Needs confirmation modal
        del self.agents[agent_name]

    @rx.event
    def add_new_config_entry(self, form_id: str): pass

    @rx.event
    def create_new_agent(self): pass


class ConfigTemplates(rx.State): 
    committed_templates: dict[str, ConfigTemplateBase] = {}
    templates: dict[str, ConfigTemplateBase] = committed_templates.copy()
    """
    ```python
    # Example:
    templates = {
        "config_name" : {
            ConfigTemplateBase(
                config_name = str,
                config_type = str,
                config = str
            )
        }
    }
    ```
    """


    @rx.var(cache=True)
    def committed_templates_list(self) -> list[str]: return list(self.committed_templates.keys())

    @rx.event
    def save_form(self, config_name: str):
        self.templates[config_name] = self.committed_templates[config_name]

    @rx.event
    def update_config_name(self, config_name: str, value: str):
        self.templates[config_name].config_name = value

    @rx.event
    def update_config_type(self, config_name: str, value: str):
        self.templates[config_name].config_type = value

    @rx.event
    def update_config(self, config_name: str, value: str):
        self.templates[config_name].config = value

    def remove_template(self, config_name: str): 
        # NOTE
        # Needs confirmation modal
        del self.templates[config_name]
        if config_name in self.committed_templates:
            del self.committed_templates[config_name]
    

class Hosts(rx.State): 
    # The plan is with this id, we can create tiles and forms from the id
    committed_hosts: dict [str, dict[str, str]] = {}

    # It's ok to copy on the mount 
    # dirty, untracked version of committed_host_forms
    hosts: dict[str, dict[str, str]] = committed_hosts.copy()

    BASE_HOST_TEMPLATE_DATA: dict[str, str] =  {
                        # host_id is the key of the dict
                        "ssh_sudo_user": "",
                        "identity_file": "~/.ssh/id_rsa",
                        "ssh_ip_address": "",
                        "ssh_port": ""
                        }

    # @rx.event
    # def remove_host(self, component_id: str):
    #     # NOTE
    #     # Needs confirmation modal
    #     del self.host_forms[component_id]

    # @rx.event
    # def save_form(self, form_id: str):

    #     # Commits to the committed host forms
    #     self.committed_host_forms[form_id] = self.host_forms[form_id]

    #     # NOTE
    #     # Confirmation modal or something like that
    #     print(f"this is my new and improved commited host:\n{json.dumps(self.committed_host_forms, indent=3)}")#logging
    #     return rx.toast.success(
    #         "Host added!",
    #         position="bottom-right"
    #     )

    # @rx.event
    # def update_form_field(self, form_id: str, field: str, value: str):
    #     working_form: dict = self.hosts[form_id]
    #     working_form[field] = value

    # @rx.event
    # def handle_selected_tile(self, component_id: str):
    #     print(f"switching host forms: {self.selected_id} --> {component_id}")
    #     self.selected_id = component_id
    
    # @rx.event
    # def generate_new_form_tile(self):
    #     def generate_new_component_id():
    #         return f"hosts{random.randint(0, 100)}"
        
    #     print("ok we are generating a new tile")
    #     while True:
    #         new_id = generate_new_component_id()
    #         if new_id not in self.host_forms:
    #             self.host_forms[new_id] = {
    #                 "host_id": "",
    #                 "ssh_sudo_user": "",
    #                 "identity_file": "~/.ssh/id_rsa",
    #                 "ssh_ip_address": "",
    #                 "ssh_port": ""
    #                 }
    #             self.selected_id = new_id
    #             return

class Platforms(rx.State): 
    platforms: dict[str, dict[str, str]] = {}
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
