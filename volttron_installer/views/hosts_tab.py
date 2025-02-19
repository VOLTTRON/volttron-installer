from time import sleep
from volttron_installer.components.base_tile import BaseForm, BaseTab, BaseTile
from flet import *
from volttron_installer.modules.attempt_to_update_control import attempt_to_update_control
from volttron_installer.modules.global_configs import global_hosts, find_dict_index
from volttron_installer.modules.global_event_bus import global_event_bus
from dataclasses import dataclass, field
import asyncio

key_constructor =[
    "host_id",
    "ssh_sudo_user",
    "identity_file",
    "ssh_ip_address",
    "ssh_port"
]


@dataclass
class Host(BaseTile):
    host_id: str
    ssh_sudo_user: str
    identity_file: str
    ssh_ip_address: str
    ssh_port: str

    tile: Container = field(init=False)
    def __post_init__(self):
        super().__init__(self.host_id)  # Initialize BaseTile with host_id
        self.tile = self.build_host_tile()

    def build_host_tile(self) -> Container:
        return self.build_tile()  # Calls BaseTile's build_tile method

class HostForm(BaseForm):
    def __init__(self, host, page: Page):
        self.host_id_field = TextField(on_change=self.validate_fields)
        self.ssh_sudo_user_field = TextField(on_change=self.validate_fields)
        self.identity_file_field = TextField(on_change=self.validate_fields)
        self.ssh_ip_address_field = TextField(on_change=self.validate_fields)
        self.ssh_port_field = TextField(on_change=self.validate_fields, on_focus=lambda _: print("meowwwws this is me being focused"))
        form_fields = {
            "Host ID" : self.host_id_field,
            "SSH SUDO USER" : self.ssh_sudo_user_field,
            "Identity File" : self.identity_file_field,
            "SSH IP Address" : self.ssh_ip_address_field,
            "SSH Port" : self.ssh_port_field
        }

        super().__init__(page, form_fields)
        self.host: Host = host
        self.revert_button.on_click = lambda _: self.revert_changes({
            self.host_id_field: self.host.host_id,
            self.ssh_sudo_user_field: self.host.ssh_sudo_user,
            self.identity_file_field: self.host.identity_file,
            self.ssh_ip_address_field: self.host.ssh_ip_address,
            self.ssh_port_field: self.host.ssh_port
            })
        self.__post_init__()

    def __post_init__(self) -> None:
        print(f"this is the compy file {self.host.identity_file}")

        # if host identity is blank
        if self.host.identity_file == "":
        # Pre-fill the identity file field with typical route
            self.host.identity_file = "~/.ssh/id_rsa/"


    async def save_config(self, e) -> None:
        old_name = self.host.host_id

        check_overwrite: bool | None = await self.check_overwrite(old_name, global_hosts, self.host_id_field.value)

        print(f" we are checking and bro is : {check_overwrite}")

        if check_overwrite == True:
            global_event_bus.publish("soft_remove", self.host.tile.key)

        elif check_overwrite == False:
            return

        # Save field values to host attributes
        self.host.ssh_sudo_user = self.ssh_sudo_user_field.value
        self.host.identity_file = self.identity_file_field.value
        self.host.ssh_ip_address = self.ssh_ip_address_field.value
        self.host.ssh_port = self.ssh_port_field.value

        # Now we can reassign new name
        self.host.host_id = self.host_id_field.value

        dictionary_appendable = {
            "ssh_sudo_user" : self.host.ssh_sudo_user,
            "identity_file" : self.host.identity_file,
            "ssh_ip_address": self.host.ssh_ip_address,
            "ssh_port": self.host.ssh_port
        }

        if check_overwrite == "rename":
            self.replace_key(global_hosts, old_key=old_name, new_key=self.host.host_id)

        global_hosts[self.host.host_id] = dictionary_appendable

        self.host.tile.content.controls[0].value = self.host.host_id
        self.page.update()
        self.write_to_file("hosts", global_hosts)
        global_event_bus.publish("update_global_ui")

        # Finalized changes UI
        self.changes_finalized(1)

class HostTab(BaseTab):
    def __init__(self, page: Page) -> None:
        self.list_of_hosts = Column(
            expand=2,
            controls=[
                OutlinedButton(text="Setup a Host", on_click=self.add_new_host)
            ]
        )
        super().__init__(self.list_of_hosts, page)
        self.page = page
        self.host_tab_view = self.tab

        global_event_bus.subscribe("tab_change", self.tab_change)

    def tab_change(self, selected_tab):
        self.refresh_tiles("hosts", global_hosts, Host, HostForm)

    def add_new_host(self, e) -> None:
        self.add_new_tile(global_hosts, "hosts", Host, HostForm)

    def build_host_setup_tab(self) -> Container:
        return self.host_tab_view
