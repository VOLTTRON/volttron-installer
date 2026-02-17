import reflex as rx
from typing import Dict, List, Optional
from ..models import Instance
from ..model_views import HostEntryModelView, PlatformModelView, PlatformConfigModelView, AgentModelView, ConfigStoreEntryModelView


class PlatformBaseState(rx.State):
    session_hydrated: bool = False
    platforms: dict[str, Instance] = {}
    _working_platform: Instance = Instance(host=HostEntryModelView(), platform=PlatformModelView())
    list_of_agents: list[AgentModelView] = []
    
    # State Vars
    @rx.var(cache=True)
    def current_uid(self) -> str:
        return self.router.page.params.get("uid", "")

    @rx.var
    def working_platform(self) -> Instance:
        self._working_platform = self.platforms.get(self.current_uid, Instance(host=HostEntryModelView(), platform=PlatformModelView()))
        return self._working_platform

    @rx.var
    def is_local_connection(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return working_platform.host.ansible_connection == "local"

    @rx.var
    def platform_deployed(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return working_platform.deployed
    
    @rx.var(cache=True)
    def in_file_platforms(self) -> list[Instance]:
        return [instance for instance in self.platforms.values() if instance.platform.in_file]
    
    @rx.var
    def platform_title(self) -> str:
        if self.current_uid == "":
            return " "
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return " "
        else:
            return working_platform.platform.safe_platform['config']['instance_name']

    @rx.var
    def password_field(self) -> str:
        if self.current_uid == "":
            return ""
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return ""
        return working_platform.password

