import reflex as rx
from typing import Dict, List, Optional
from ..models import Instance
from ..model_views import HostEntryModelView, PlatformModelView, PlatformConfigModelView, AgentModelView, ConfigStoreEntryModelView


class DevicePlatformGroup(rx.Base):
    group_key: str = ""
    device_label: str = ""
    ansible_host: str = ""
    ansible_user: str = ""
    instance_count: int = 0
    deployed_count: int = 0
    instances: list[Instance] = []


class PlatformBaseState(rx.State):
    session_hydrated: bool = False
    platforms: dict[str, Instance] = {}
    _working_platform: Instance = Instance(host=HostEntryModelView(), platform=PlatformModelView())
    list_of_agents: list[AgentModelView] = []

    # Dynamically fetched agent lists
    github_agents: list[AgentModelView] = []
    local_agents: list[AgentModelView] = []
    github_agents_loading: bool = False
    github_agents_offline: bool = False
    local_agents_loading: bool = False
    
    # State Vars
    @rx.var
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

    @staticmethod
    def _normalize_device_key(instance: Instance) -> str:
        if instance.host.ansible_connection == "local":
            return "local"

        host = (instance.host.ansible_host or "").strip().lower()
        if host:
            return host

        return "unknown"

    @rx.var(cache=True)
    def in_file_platform_groups(self) -> list[DevicePlatformGroup]:
        groups: dict[str, DevicePlatformGroup] = {}

        for instance in self.in_file_platforms:
            group_key = self._normalize_device_key(instance)

            if instance.host.ansible_connection == "local":
                device_label = "Local Device"
            elif instance.host.ansible_host:
                device_label = instance.host.ansible_host
            else:
                device_label = "Unknown Device"

            if group_key not in groups:
                groups[group_key] = DevicePlatformGroup(
                    group_key=group_key,
                    device_label=device_label,
                    ansible_host=instance.host.ansible_host,
                    ansible_user=instance.host.ansible_user,
                    instances=[],
                )

            groups[group_key].instances.append(instance)

            if not groups[group_key].ansible_user and instance.host.ansible_user:
                groups[group_key].ansible_user = instance.host.ansible_user

        sorted_groups = sorted(
            groups.values(),
            key=lambda g: g.device_label.lower(),
        )

        for group in sorted_groups:
            group_instances = sorted(
                group.instances,
                key=lambda i: i.platform.config.instance_name.lower(),
            )
            group.instances = group_instances
            group.instance_count = len(group_instances)
            group.deployed_count = len([i for i in group_instances if i.deployed])

        return sorted_groups

    @rx.var
    def total_device_count(self) -> int:
        return len(self.in_file_platform_groups)

    @rx.var
    def deployed_device_count(self) -> int:
        return len([g for g in self.in_file_platform_groups if g.deployed_count > 0])

    @rx.var
    def local_instance_count(self) -> int:
        return len([i for i in self.in_file_platforms if i.host.ansible_connection == "local"])

    @rx.var
    def remote_instance_count(self) -> int:
        return len([i for i in self.in_file_platforms if i.host.ansible_connection != "local"])

    @rx.var
    def home_featured_instance(self) -> Instance:
        deployed = [i for i in self.in_file_platforms if i.deployed]
        if deployed:
            return deployed[-1]
        if self.in_file_platforms:
            return self.in_file_platforms[-1]
        return Instance(host=HostEntryModelView(), platform=PlatformModelView())

    @staticmethod
    def _sanitize_instance_suffix(instance_name: str) -> str:
        sanitized = "".join(
            char if (char.isalnum() or char in "_-") else "-"
            for char in (instance_name or "")
        )
        sanitized = sanitized.strip("-")
        return sanitized or "instance"

    @rx.var
    def effective_volttron_home(self) -> str:
        if self.current_uid == "":
            return "~/.volttron"

        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return "~/.volttron"

        base_home = working_platform.host.volttron_home or "~/.volttron"
        suffix = self._sanitize_instance_suffix(working_platform.platform.config.instance_name)
        if base_home.strip() == "~/.volttron":
            return f"~/.volttron/instances/{suffix}"
        return f"{base_home}.{suffix}"

    @rx.var
    def effective_volttron_venv(self) -> str:
        if self.current_uid == "":
            return "~/volttron.venv"

        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return "~/volttron.venv"

        base_venv = working_platform.host.volttron_venv or "~/volttron.venv"
        suffix = self._sanitize_instance_suffix(working_platform.platform.config.instance_name)
        if base_venv.strip() == "~/volttron.venv":
            return f"~/.volttron/venvs/{suffix}"
        return f"{base_venv}.{suffix}"

    @rx.var
    def has_any_instance(self) -> bool:
        return len(self.in_file_platforms) > 0

    @rx.var
    def deployed_instances(self) -> list[Instance]:
        return [i for i in self.in_file_platforms if i.deployed]

    @rx.var
    def total_instance_count(self) -> int:
        return len(self.in_file_platforms)

    @rx.var
    def deployed_instance_count(self) -> int:
        return len([i for i in self.in_file_platforms if i.deployed])
    
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

