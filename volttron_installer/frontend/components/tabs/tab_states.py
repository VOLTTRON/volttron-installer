import reflex as rx
# from .....backend.models import CreateInventoryRequest, Inventory, HostEntry, ConfigStoreEntry, AgentDefinition, PlatformDefinition
from pydantic import BaseModel
from typing import Literal

"""
2/18/24
The problem with this iteration, is that all of the hosts and agents and templates are still stored in
their respective tabs, which was a big reason I wanted to use this method in the first place. I guess the real
advantage is the fact that we could leverage rx.Base, but we have the backend already. Type safety is good but
my whole process is def much slower because we're going to have to iterate through the list in a for loop.
Also, there's a trade off with handling duplicate forms, its harder to verify that its being duplicated, 
because we have to iterate through the the list of x_tab_content and get each x_entry.y and see if our working
x_entry has a conflict. But it's easier in the fact that if it's a duplicate, and we replace, we dont have to 
replace the in the exact index with the same values as we would in a dict, we just override the conflict.
"""

HOST_ENTRY_FIELDS = Literal["host_id", "ssh_sudo_user", "identity_file", "ssh_ip_address", "ssh_port"]
AGENT_ENTRY_FIELDS = Literal["agent_name", "identity", "agent_path", "agent_config", "config_store_entries"]

class BaseHostContent(rx.Base):
    host_id: str = ""
    ssh_sudo_user: str = ""
    identity_file: str = "~/.ssh/id_rsa"
    ssh_ip_address: str = ""
    ssh_port: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "host_id": self.host_id,
            "ssh_sudo_user": self.ssh_sudo_user,
            "identity_file": self.identity_file,
            "ssh_ip_address": self.ssh_ip_address,
            "ssh_port": self.ssh_port,
        }


class HostTabContent(rx.Base):
    tab_content_id: str
    host_entry: BaseHostContent

    # I want to use a method to like this to compare individual fields. but this implementation doesn't work sadly
    original_host_entry: dict
    
    # Unsaved changes detected, by default all content is uncaught.
    uncaught: bool = True

    # If the host content is committed, by default they aren't
    committed: bool = False

    def has_uncaught_changes(self) -> bool:
        current_host_entry = self.host_entry.to_dict()
        result = current_host_entry != self.original_host_entry
        return result


class HostTab(rx.State):
    list_of_host_tab_content: list[HostTabContent] = []
    selected_id: str = ""

    _committed_hosts = [tab_content.host_entry.host_id for tab_content in list_of_host_tab_content if tab_content.committed]

    # Vars
    @rx.var(cache=True)
    def committed_hosts(self) -> list[str]:
        """List of committed hosts' ids"""
        # return self._committed_hosts
        hosts: list[str]= []
        for tab_content in self.list_of_host_tab_content:
            if tab_content.committed:
                # We use the original host_entry dict because its the most recent committed state of the host entry
                hosts.append(tab_content.original_host_entry["host_id"])
        return hosts

    # Events
    @rx.event
    def update_host_detail(self, host_tab_content_id, field: HOST_ENTRY_FIELDS, value: str):
        for i in self.list_of_host_tab_content:
            if i.tab_content_id == host_tab_content_id:
                i.uncaught = i.has_uncaught_changes()
                print(i.original_host_entry)
                print(i.host_entry.to_dict())
                print(i.has_uncaught_changes())
                setattr(i.host_entry, field, value)
                # print("uncaught??:", i.has_uncaught_changes())

    @rx.event
    def refresh_selected_id(self, id: str):
        self.selected_id = id

    @rx.event
    def append_new_content(self):
        unique_tab_content_uid = f"baka{len(self.list_of_host_tab_content)}"
        new_host_entry = BaseHostContent()
        # print(f"ok brooo this is what i got and stuff:\n{new_host_entry.to_dict()}")
        new_tab_content = HostTabContent(
            host_entry=new_host_entry,
            tab_content_id=unique_tab_content_uid,
            original_host_entry=new_host_entry.to_dict()
            )

        self.list_of_host_tab_content.append(new_tab_content)
        self.selected_id = unique_tab_content_uid

    @rx.event
    def commit_host(self, passed_tab_content_id: str):
        for tab_content in self.list_of_host_tab_content:
            if tab_content.tab_content_id == passed_tab_content_id:
                working_content = tab_content
                working_content.original_host_entry = tab_content.host_entry.to_dict()
                break
        working_content.committed = True
        working_content.uncaught = False
        yield rx.toast.success("Host Saved!")


class BaseAgentContent(rx.Base):
    agent_name: str = ""
    identity: str = ""
    agent_path: str = ""
    agent_config: str = ""
    config_store_entries: dict = {}

    def to_dict(self) -> dict[str, str]:
        return {
            "agent_name": self.agent_name,
            "identity": self.identity,
            "agent_path": self.agent_path,
            "agent_config": self.agent_config,
            "config_store_entries": self.config_store_entries,
        }


class AgentTabContent(rx.Base):
    tab_content_id: str
    agent_entry: BaseAgentContent

    # I want to use a method to like this to compare individual fields. but this implementation doesn't work sadly
    original_agent_entry: dict
    
    # Unsaved changes detected, by default all content is uncaught.
    uncaught: bool = True

    # If the host content is committed, by default they aren't
    committed: bool = False

    def has_uncaught_changes(self) -> bool:
        current_agent_entry = self.agent_entry.to_dict()
        result = current_agent_entry != self.original_agent_entry
        return result


class AgentSetupTab(rx.State):
    list_of_agent_tab_content: list[AgentTabContent] = []
    selected_id: str = ""

    _committed_hosts = [tab_content.agent_entry.agent_name for tab_content in list_of_agent_tab_content if tab_content.committed]

    # Vars
    @rx.var(cache=True)
    def committed_agents(self) -> list[str]:
        # return self._committed_hosts
        hosts: list[str]= []
        for tab_content in self.list_of_agent_tab_content:
            if tab_content.committed:
                # We use the original host_entry dict because its the most recent committed state of the host entry
                hosts.append(tab_content.original_agent_entry["agent_name"])
        return hosts

    # Events
    @rx.event
    def update_agent_detail(self, agent_tab_content_id, field: AGENT_ENTRY_FIELDS, value: str):
        for i in self.list_of_agent_tab_content:
            if i.tab_content_id == agent_tab_content_id:
                i.uncaught = i.has_uncaught_changes()
                setattr(i.agent_entry, field, value)
                # print("uncaught??:", i.has_uncaught_changes())

    @rx.event
    def refresh_selected_id(self, id: str):
        self.selected_id = id

    @rx.event
    def append_new_content(self):
        unique_tab_content_uid = f"apple{len(self.list_of_agent_tab_content)}"
        new_agent_entry = BaseAgentContent()
        # print(f"ok brooo this is what i got and stuff:\n{new_host_entry.to_dict()}")
        new_tab_content = AgentTabContent(
            tab_content_id=unique_tab_content_uid,
            agent_entry=new_agent_entry,
            original_agent_entry=new_agent_entry.to_dict()
            )

        self.list_of_agent_tab_content.append(new_tab_content)
        self.selected_id = unique_tab_content_uid

    @rx.event
    def commit_agent(self, passed_tab_content_id: str):
        for tab_content in self.list_of_agent_tab_content:
            if tab_content.tab_content_id == passed_tab_content_id:
                working_content = tab_content
                working_content.original_agent_entry = tab_content.agent_entry.to_dict()
                break
        working_content.committed = True
        working_content.uncaught = False
        yield rx.toast.success("Host Saved!")
