import pprint
import typing
import reflex as rx
import random
import asyncio
import string
import json
from ...navigation.state import NavigationState
from .base import BASE_CONFIG_TEMPLATE_DATA, BASE_TYPE_ANNOTATION, BASE_AGENT_DATA, BASE_PLATFORM_DATA

# TODO
# All of these states have very similar functionality, i want a way for these
# states to inherit such functionality.


class HostsTabState(rx.State):   

    # The plan is with this id, we can create tiles and forms from the id
    committed_host_forms: dict [str, dict[str, str]] = {
                    "kingfort": {
                        "host_id": "king fortnite",
                        "ssh_sudo_user": "",
                        "identity_file": "~/.ssh/id_rsa",
                        "ssh_ip_address": "",
                        "ssh_port": ""
                    }
    }

    # dirty, untracked version of committed_host_forms
    host_forms: dict[str, dict[str, str]] = committed_host_forms.copy()

    selected_id: str = ""

    @rx.event
    def remove_host(self, component_id: str):
        # NOTE
        # Needs confirmation modal
        del self.host_forms[component_id]

    @rx.event
    def save_form(self, form_id: str):

        # Commits to the committed host forms
        self.committed_host_forms[form_id] = self.host_forms[form_id]

        # NOTE
        # Confirmation modal or something like that
        print(f"this is my new and improved commited host:\n{json.dumps(self.committed_host_forms, indent=3)}")#logging

    @rx.event
    def update_form_field(self, form_id: str, field: str, value: str):
        working_form: dict = self.host_forms[form_id]
        working_form[field] = value

    @rx.event
    def handle_selected_tile(self, component_id: str):
        print(f"switching host forms: {self.selected_id} --> {component_id}")
        self.selected_id = component_id
    
    @rx.event
    def generate_new_form_tile(self):
        def generate_new_component_id():
            return f"hosts{random.randint(0, 100)}"
        
        print("ok we are generating a new tile")
        while True:
            new_id = generate_new_component_id()
            if new_id not in self.host_forms:
                self.host_forms[new_id] = {
                    "host_id": "",
                    "ssh_sudo_user": "",
                    "identity_file": "~/.ssh/id_rsa",
                    "ssh_ip_address": "",
                    "ssh_port": ""
                    }
                return

class AgentSetupTabState(rx.State):
    committed_agent_forms: dict[str, dict[str, str]] = {}
    agent_forms: dict[str, dict[str, str]] = committed_agent_forms.copy()

    selected_id: str = ""

    @rx.event
    def handle_config_submit(self):
        print("we saved")

    @rx.event
    def save_form(self, form_id: str):

        self.committed_agent_forms[form_id] = self.agent_forms[form_id]

        print("we saved the form to committed forms")
        print("it looks like this now")
        print(self.committed_agent_forms)

    @rx.event
    def handle_selected_tile(self, component_id: str):
        print(f"switching agent forms: {self.selected_id} --> {component_id}")
        self.selected_id = component_id

    @rx.event
    def update_form_field(self, form_id: str, field: str, value: str):
        working_form: dict = self.agent_forms[form_id]
        working_form[field] = value

    @rx.event
    def remove_form(self, component_id: str):
        # NOTE
        # Needs confirmation modal
        del self.agent_forms[component_id]

    @rx.event
    def generate_new_form_tile(self):
        def generate_new_component_id():
            return f"agent-component-{random.randint(0, 100)}"
        
        while True:
            new_id = generate_new_component_id()
            if new_id not in self.agent_forms:
                self.agent_forms[new_id] = BASE_AGENT_DATA.copy()
                return

class ConfigTemplatesTabState(rx.State):
    committed_template_forms: dict[str, dict[str, str]] = {}
    config_template_forms: dict[str, dict[str, str]] = committed_template_forms.copy()
    
    selected_id: str = ""

    @rx.event
    def save_form(self, form_id: str):

        self.committed_template_forms[form_id] = self.config_template_forms[form_id]

    @rx.event
    def handle_selected_tile(self, component_id: str):
        print(f"switching host forms: {self.selected_id} --> {component_id}")
        self.selected_id = component_id

    @rx.event
    def update_form_field(self, form_id: str, field: str, value: str):
        working_form: dict = self.config_template_forms[form_id]
        working_form[field] = value

    @rx.event
    def remove_template(self, component_id: str):
        # NOTE
        # Needs confirmation modal
        del self.config_template_forms[component_id]

    @rx.event
    def generate_new_form_tile(self):
        def generate_new_component_id():
            return f"template-component-{random.randint(0, 100)}"
        
        while True:
            new_id = generate_new_component_id()
            if new_id not in self.config_template_forms:
                self.config_template_forms[new_id] = BASE_CONFIG_TEMPLATE_DATA.copy()
                return

class PlatformOverviewState(rx.State):
    platforms: dict[str, dict[str, str]] = {}

    def generate_unique_uid(self, length=7) -> str:
        characters = string.ascii_letters + string.digits
        while True:
            new_uid = ''.join(random.choice(characters) for _ in range(length))
            if new_uid not in self.platforms:
                return new_uid

    @rx.event
    async def generate_new_platform(self):
        # test
        import json

        new_uid = self.generate_unique_uid()
        self.platforms[new_uid] = BASE_PLATFORM_DATA.copy()
        nav_state = await self.get_state(NavigationState)
        await nav_state.add_platform_route(new_uid)
        print(f"we literally made bro: {new_uid}")
        print("this is bro like this is him:")
        print(json.dumps(self.platforms, indent=4))
        print("\n\n")
        # return rx.redirect(f"/platform/{new_uid}")

    @rx.event 
    async def remove_platform(self, uid: str):
        if uid in self.platforms:
            del self.platforms[uid]
            nav_state = await self.get_state(NavigationState)
            await nav_state.remove_platform_route(uid)
            return rx.redirect("/")
    
    @rx.event
    def update_form_field(self, platform_uid: str, field: str, value: str):
        if platform_uid in self.platforms:
            self.platforms[platform_uid][field] = value
            print(f"updated {field} with {value} for {platform_uid}")
        
class PlatformState(rx.State):
    @rx.var(cache=True)
    def current_uid(self) -> str:
        return self.router.page.params.get("uid", "")
    
    @rx.var(cache=True)
    def platform_data(self) -> dict:
        uid = self.current_uid
        return PlatformOverviewState.platforms.get(uid, {})