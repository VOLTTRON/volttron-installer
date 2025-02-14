import pprint
import typing
import reflex as rx
import random
import asyncio
import string
import json
from ..form_components import *
from ...navigation.state import NavigationState
from ...modules.state import Agents, Hosts, ConfigTemplates
from ...modules.base import HostBase, ConfigTemplateBase
from ..buttons.delete_icon_button import delete_icon_button
from .base import BASE_CONFIG_TEMPLATE_DATA, BASE_TYPE_ANNOTATION, BASE_AGENT_DATA, BASE_PLATFORM_DATA

# TODO
# All of these states have very similar functionality, i want a way for these
# states to inherit such functionality.


class HostsTabState(rx.State):   

    # The plan is with this id, we can create tiles and forms from the id
    committed_host_forms: dict [str, dict[str, str]] = {}

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
        return rx.toast.success(
            "Host added!",
            position="bottom-right"
        )

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
                self.selected_id = new_id
                return

class AgentSetupTabState(rx.State):
    committed_agent_forms: dict[str, dict[str, str]] = {}
    # {
    #   comopnent id : {
    #               "info" : "moreinfo"
    #              }
    # }
    agent_forms:           dict[str, dict[str, str]] = committed_agent_forms.copy()
    selected_id: str = ""

    selected_config_store_entry: str = ""

    _committed_agents_list: list[str] = []

    @rx.var(cache=True)
    def committed_agents_list(self) -> list[str]:
        # accessing the keys of the committed_agent_forms var two layers deep
        result = []
        for component_id in list(self.committed_agent_forms.keys()):
            result.append(self.committed_agent_forms[component_id]["agent_name"])
        return result


    @rx.event
    async def handle_config_submit(self, data: dict[str, str], component_id: str):
        print("we saved {data}", data)
        print(f"yeah but do we have our comp id?: {component_id}")
        template = data["template"]
        custom_template_name = data["config_name"]
        if template == "":
            self.agent_forms[component_id]["agent_config_store"][custom_template_name] = BASE_CONFIG_TEMPLATE_DATA.copy()
        else:
            # NOTE:
            # Problem, how are we going to get the config_template_state data through the committed_forms?
            # underneath the {
            #     "component_id" : {"template" : "info"}
            # } structure? Theres no way to access it besides somehow having the component id. either in the select
            # we can somehow pass in the component_id : config_name key value pair, or we have a new system to store data
            # that would look like {"config_name" : "rest"}
            config_template_state: ConfigTemplatesTabState = await self.get_state(ConfigTemplatesTabState)
            committed_templates_list = config_template_state.committed_templates_list
            
            print(template in committed_templates_list)
            print(template)
            print(committed_templates_list)
            
            if template in committed_templates_list:
                deep_index = committed_templates_list.index(template)
                template_comp_id = list(config_template_state.committed_template_forms.keys())[deep_index]
                self.agent_forms[component_id]["agent_config_store"][custom_template_name] = config_template_state.committed_template_forms[template_comp_id]
        print(self.agent_forms)

    @rx.event
    def change_selected_config_entry(self, config_name: str):
        self.selected_config_store_entry = config_name

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
                self.selected_id = new_id
                return

class ConfigTemplatesTabState(rx.State):
    committed_template_forms: dict[str, dict[str, str]] = {}
    config_template_forms: dict[str, dict[str, str]] = committed_template_forms.copy()
    
    selected_id: str = ""

    # Vars
    @rx.var(cache=True)
    def committed_templates_list(self) -> list[str]:
        result = []
        for component_id in list(self.committed_template_forms.keys()):
            result.append(self.committed_template_forms[component_id]["config_name"])
        return result

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
                self.selected_id = new_id
                return

class PlatformOverviewState(rx.State):
    platforms: dict[str, dict[str, str]] = {}

    selected_agent_component_id: str = ""

    working_platform: str = ""
    render_component: str = ""

    selected_agent_config_template_id: str = ""

    # Vars
    @rx.var(cache=True)
    def get_agent_name(self) -> str:
        if self.working_platform and self.render_component:
            try:
                return self.platforms[self.working_platform]["agents"][self.render_component]["agent_name"]
            except KeyError:
                return ""
        return ""

    @rx.var(cache=True)
    def agents_added_list(self) -> dict[str, list[str]]: 
        # Go through every platform, grab keys of their added agent, return dict
        result = {}
        for platform_uid in list(self.platforms.keys()):
            result[platform_uid] = list(self.platforms[platform_uid]["agents"].keys())

        return result

    def grab_agent_name(self, agent_component_id):
        ...

    def generate_unique_uid(self, length=7) -> str:
        characters = string.ascii_letters + string.digits
        while True:
            new_uid = ''.join(random.choice(characters) for _ in range(length))
            if new_uid not in self.platforms:
                return new_uid

    # Events
    @rx.event
    def handle_selected_agent(self, agent_component_id): 
        self.selected_agent_component_id = agent_component_id

    @rx.event
    async def generate_new_platform(self):
        new_uid = self.generate_unique_uid()
        self.platforms[new_uid] = BASE_PLATFORM_DATA.copy()
        nav_state: NavigationState = await self.get_state(NavigationState)
        await nav_state.add_platform_route(new_uid)

        # logging
        import json

        print(f"we literally made bro: {new_uid}")
        print("this is bro like this is him:")
        print(json.dumps(self.platforms, indent=4))
        print("\n\n")
        # return rx.redirect(f"/platform/{new_uid}")

    @rx.event 
    async def remove_platform(self, uid: str):
        if uid in self.platforms:
            del self.platforms[uid]
            nav_state: NavigationState = await self.get_state(NavigationState)
            await nav_state.remove_platform_route(uid)
            return rx.redirect("/")
    
    @rx.event
    async def add_agent(self, agent_name: str, uid: str):
        agent_state: AgentSetupTabState = await self.get_state(AgentSetupTabState)
        
        # Get the index of our agent_name in the agent_list, 
        # so we can get the "index" of the dict one above it
        # because every value in the list was from one entry of the 
        # dict above it
        agent_name = agent_name["agent_name"]
        print(agent_state.committed_agents_list)

        deep_index = agent_state.committed_agents_list.index(agent_name)

        # Find the component id we are working with in committed forms
        component_id = list(agent_state.committed_agent_forms.keys())[deep_index]

        # Grab the contents of the committed agent
        agent = agent_state.committed_agent_forms[component_id]

        # Now we can put it all together
        self.platforms[uid]["agents"][f"platform-{uid}-agent-{random.randint(0, 110)}{agent_name[0]}"] = agent
        # This is really big problem, we are becomming too nested:
        # with this method, our structure now looks like, platform: 
        #                                      agents: 
        #                                            agent_component_id: 
        #                                                           agent_data
        # when our structure is now like this


    @rx.event
    def update_form_field(self, platform_uid: str, agent_component_id: str, value: str):
        if platform_uid in self.platforms:
            self.platforms[platform_uid]["agents"][agent_component_id]["agent_config"] = value
            print(f"updated  with {value} for {platform_uid}")
        


class PlatformState(rx.State):
    @rx.var(cache=True)
    def current_uid(self) -> str:
        return self.router.page.params.get("uid", "")
    
    @rx.var(cache=True)
    def platform_data(self) -> dict:
        uid = self.current_uid
        return PlatformOverviewState.platforms.get(uid, {})


# ==================== TRYING A NEW WAY OF DOING THINGS =========================
# In essence, I want to delegate ALL ui generation to these tab states, and all edits of content
# should be handled by the module's state.

# This in theory, should eliminate the use of heavily nested form content under the form UID's.

class AgentSetupTab(rx.State):
    selected_component_id: str = ""
    disabled_submit: bool = True

    # Backend Var
    _form_agent_ids : dict[str, str] = {}

    # Vars
    # @rx.var(cache=True)
    # def form_agent_ids(self) -> dict[str, str]:
    
    #     result = {}
    #     agent_state: Agents = self.get_state(Agents)
    
    #     for i in agent_state.committed_agents_list:
    #         while True:
    #             form_uid = self.generate_new_component_id()
    #             if form_uid not in result:
    #                 result[form_uid] = i
    #     return result

    @rx.event
    def handle_selected_tile(self, component_id: str):
        print(f"switching agent forms: {self.selected_id} --> {component_id}")
        self.selected_id = component_id

    @rx.event
    def create_blank_form(self):
        self.form_agent_ids

    def agent_to_uid(self):
        return rx.foreach

    # So what i want to happen here is that the form is generated off of the Agents dict
    # Goal here is that i want to generate an uncaught form like the ones
    # we have in the Flet ver.
    def generate_form_tile(self, form_agent_entry: tuple[str, str]) -> rx.Component:
        form_uid, agent_name = form_agent_entry
        
        return form_selection_button.form_selection_button(
                text=agent_name,
                selection_id=form_uid,
                selected_item=self.selected_component_id,
                on_click = self.handle_selected_tile(form_uid),
                delete_component=delete_icon_button()
            )


    def generate_new_component_id(self):
        import random
        return f"agent-component-{random.randint(0, 300)}"



#   so the idea of this is to have the components create all of the components and stuff like that 
class ConfigTemplatesTab(ConfigTemplates):
    selected_id: str = ""
    disabled_submit: bool = False

    _config_form_uids: dict[str, str] = {}

    @rx.var(cache=True)
    def config_form_uids(self) -> dict[str, str]: 
        form_uids = {}
        for config_name in list(self.templates.keys()):
            uid = generate_new_component_id("config_template")
            form_uids[uid] = config_name
                
        _config_form_uids = form_uids
        return _config_form_uids

    @rx.event
    def handle_selected_id(self, component_id: str):
        self.selected_id = component_id

    @rx.event
    def create_blank_form(self):
        uid = generate_new_component_id("config_template")
        while uid in self._config_form_uids:
            uid = generate_new_component_id("config_template")
        self._config_form_uids[uid] = ""  # Modify the state var instead
        print("hahahhahahaha[ah fpiohfap ]", self._config_form_uids)

    @rx.event
    def get_data(self, form_uid: str):
        return self.config_form_uids[form_uid]




#   
# class ConfigTemplatesTab(rx.State):
#     selected_id: str = ""
#     disabled_submit: bool = False

#     _config_form_uids: dict[str, str] = {}

#     @rx.var(cache=True)
#     def config_form_uids(self) -> dict[str, str]: return self._config_form_uids

#     @rx.event
#     def handle_selected_id(self, component_id: str):
#         self.selected_id = component_id

#     @rx.event
#     def create_blank_form(self):
#         while True:
#             uid = generate_new_component_id("config_template")
#             if uid not in self.config_form_uids:
#                 self.config_form_uids[uid] = ""

#     @rx.event
#     def get_data(self, form_uid: str):
#         return self.config_form_uids[form_uid]

#     @classmethod
#     def assign_form_id(self, config_template: tuple[str, rx.Base]) -> rx.Component:
#         config_name = config_template[0]
#         new_form_uid = ""
#         while True:
#             uid = generate_new_component_id("config_template")
#             if uid not in self.config_form_uids:
#                 self.config_form_uids[uid] = config_template
#                 new_form_uid = uid
#                 break

#         return form_selection_button.form_selection_button(
#             text=rx.cond(
#                 self.committed_template_forms.contains(new_form_uid),
#                 self.committed_template_forms[new_form_uid]["config_name"],
#                 ""
#             ),
#             selection_id=new_form_uid,
#             selected_item=self.selected_id,
#             on_click = self.handle_selected_tile(new_form_uid),
#             delete_component=delete_icon_button()
#         )



class HostsTab(rx.State):
    selected_id: str = ""
    form_selection: dict[str, str]

    @rx.event
    def switch_form_id(self, form_uid):
        self.selected_id = form_uid

    @classmethod
    def create_form_ids(self, host_id) -> rx.Component:
        host_state: Hosts = self.get_state(Hosts) 



class PlatformAgentConfigState(rx.State):

    active_platform_agent_component_id: str = ""


def generate_new_component_id(type: str = "___"):
    import random
    return f"{type}-component-{random.randint(0, 300)}"


# ============================= END =======================