"""Host and inventory data models."""

from typing import Literal
from pydantic import BaseModel, Field


class HostEntry(BaseModel):
    """
    A `HostEntry` represents a single entry in the inventory.  It is a single
    VOLTTRON instance connection point.
    """
    id: str
    ansible_user: str
    ansible_host: str
    ansible_port: int = Field(default=22)
    ansible_connection: Literal["ssh", "local"] = "ssh"
    http_proxy: str | None = None
    https_proxy: str | None = None
    volttron_venv: str = "~/volttron.venv"
    volttron_home: str = "~/.volttron"
    volttron_source: str = "~/volttron"  # Path to VOLTTRON source for monolithic installations
    host_configs_dir: str | None = None
    instance_name: str | None = None
    ignore_host_keys: bool = False

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "ansible_user": self.ansible_user,
            "ansible_host": self.ansible_host,
            "ansible_port": int(self.ansible_port),
            "ansible_connection": self.ansible_connection,
            "http_proxy": "" if self.http_proxy is None else self.http_proxy,
            "https_proxy": "" if self.https_proxy is None else self.https_proxy,
            "volttron_venv": "" if self.volttron_venv is None else self.volttron_venv,
            "volttron_home": self.volttron_home,
            "volttron_source": self.volttron_source,
            "host_configs_dir": "" if self.host_configs_dir is None else self.host_configs_dir,
            "instance_name": "" if self.instance_name is None else self.instance_name,
        }


class CreateOrUpdateHostEntryRequest(HostEntry):
    """Request model for creating or updating a host entry"""
    pass


class RemoveHostEntryRequest(BaseModel):
    """Request model for removing a host entry"""
    id: str


class ReachableResponse(BaseModel):
    reachable: bool = True