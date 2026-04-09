"""PlatformValidationState - Validation computed vars and host reachability checks."""

import re
from loguru import logger

import reflex as rx

from ..models import Instance

from .platform_crud import PlatformCrudState


class PlatformValidationState(PlatformCrudState):
    _host_resolvable: bool = True
    _host_pinging: bool = False

    # this var tracks if the host_id that the user is inputting is resolved.
    # as the user inputs a host, we make sure this is false inside of self.update_detail,
    # so we cant save the instance until the host text box has been blurred. once it has,
    # we can check if the host is reachable or not. if it is, we set this to true.
    _host_resolved: bool = False

    # Vars
    @rx.var
    def new_agents_list(self) -> list[str]:
        if self.current_uid == "":
            return []
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return []
        # logger.debug(f"nah because new agents are : {[agent.identity for agent in working_platform.platform.agents.values() if not agent.is_new]}")
        return [agent.identity for agent in working_platform.platform.agents.values() if not agent.is_new]

    # ==== vars for connection validation ===
    @rx.var
    def host_resolved(self) -> bool: return self._host_resolved

    @rx.var
    def connection_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[0]

    @rx.var
    def host_pinging(self) -> bool:
        return self._host_pinging

    @rx.var
    def is_host_resolvable(self) -> bool:
        return self._host_resolvable


    @rx.var
    def connection_id_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[1]["id"]

    @rx.var
    def connection_ansible_user_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[1]["ansible_user"]

    @rx.var
    def connection_ansible_host_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[1]["ansible_host"]

    @rx.var
    def connection_ansible_port_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[1]["ansible_port"]

    # ==== vars for platform validation ===
    @rx.var
    def platform_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.platform_validity(working_platform)[0]

    @rx.var
    def platform_instance_name_validity(self)-> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.platform_validity(working_platform)[1]["instance_name"]

    @rx.var
    def platform_instance_name_not_in_use(self)-> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.platform_validity(working_platform)[1]["instance_name_not_used"]

    @rx.var
    def platform_vip_address_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.platform_validity(working_platform)[1]["vip_address"]
    # === end of platform validation vars ===

    # === vars for instance validation ===
    @rx.var
    def instance_savable(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        else:
            return self.check_instance_savable(working_platform)

    @rx.var
    def instance_uncaught(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        else:
            return self.check_instance_uncaught(working_platform)

    @rx.var
    def instance_deployable(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.check_instance_deployable(working_platform)
    # === end of instance validation bars ===

    @rx.event
    async def determine_host_reachability(self, working_platform: Instance):
        """On blur of host field, check if the host is reachable"""
        from ..thin_endpoint_wrappers import ping_resolvable_host
        # Skip pinging for local connections -- localhost is always reachable
        if working_platform.host.ansible_connection == "local":
            self._host_resolvable = True
            self._host_pinging = False
            self._host_resolved = True
            yield
            return

        # we have these yield statements scattered because we need make sure when a state var
        # is updated, the app can see it in real time as the function executes. if we dont have it
        # our UI handling the real time spinner will not work as the UI wont be able to read the changed
        # var in real time
        self._host_pinging = True
        yield
        self._host_resolvable = await self.check_host_reachable(working_platform)
        self._host_pinging = False
        yield
        self._host_resolved = self._host_resolvable
        yield
        return

    @rx.event
    def cement_registry_config(self, working_platform: Instance):
        logger.debug("Cementing registry config...")
        self.platforms[working_platform.platform.config.instance_name] = working_platform

    # NOTE: i would like to offload the uncaught and valid vars into the state vars because it's easier for the UI to read off of
    # state vars, for faster development, ive kept these here and i'll change it once it's time to refine the code.
    #   Secondary NOTE: not sure if i've already made changes.
    def handle_uncaught(self, working_platform: Instance):
        working_platform.uncaught = working_platform.has_uncaught_changes()

    def handle_validity(self, working_platform: Instance):
        working_platform.valid = not working_platform.does_host_have_errors()

    # generate_unique_uid is now inherited from PlatformCrudState

    # functions to check if things are savable, reachable, valid, uncaught.
    async def check_host_reachable(self, working_platform: Instance) -> bool:
        from ..thin_endpoint_wrappers import ping_resolvable_host
        host_id = working_platform.host.id
        if host_id =="":
            return False
        response = await ping_resolvable_host(host_id)
        return response.reachable

    def check_instance_uncaught(self, working_platform: Instance) -> bool:
        uncaught: bool = False
        # check if host details are changed
        if working_platform.host.to_dict() != working_platform.safe_host_entry:
            uncaught = True

        # check if platform details are changed but skip the agents field as we will handle that separately
        if {k: v for k, v in working_platform.platform.to_dict().items() if k != 'agents'} != {k: v for k, v in working_platform.platform.safe_platform.items() if k != 'agents'}:
            uncaught = True

        # check if we added some new uncaught agents
        for agent in working_platform.platform.agents.values():
            if agent.is_new:
                logger.debug(f"we found an uncaught agent")
                uncaught = True
                # we can break out of this because we just needed to find at least one brand new uncaught agent
                # to render the platform as uncaught
                break

        return uncaught

    def check_instance_savable(self, working_platform: Instance) -> bool:
        savable = True

        # manually check the host and all of its stuff...
        host_dict = working_platform.host.to_dict()
        is_local = host_dict.get("ansible_connection") == "local"

        # Basic field checks apply to all connection types
        if (
            host_dict["id"] == "" or \
            host_dict["ansible_user"] == "" or \
            host_dict["ansible_port"].isdigit() == False or \
            host_dict["ansible_host"] == ""
        ):
            logger.debug("Host basic fields are not valid...")
            logger.debug(f"Host ID is empty: {host_dict['id'] == ''}")
            logger.debug(f"Ansible user is empty: {host_dict['ansible_user'] == ''}")
            logger.debug(f"Ansible port is not numeric: {host_dict['ansible_port'].isdigit() == False}")
            logger.debug(f"Ansible host is empty: {host_dict['ansible_host'] == ''}")
            savable = False

        # Host reachability checks only apply to non-local (SSH) connections
        if not is_local and (
            self.is_host_resolvable == False or \
            self.host_pinging or \
            self.host_resolved == False
        ):
            logger.debug("Host reachability is not valid...")
            logger.debug(f"Host is not resolvable: {self.is_host_resolvable == False}")
            logger.debug(f"Host is currently pinging: {self.host_pinging}")
            logger.debug(f"Host is not resolved: {self.host_resolved == False}")
            logger.debug(f"Here is the host to prove: {host_dict}")
            savable = False

        # check if platform details are valid
        platform_valid, platform_valid_map = self.platform_validity(working_platform)
        if platform_valid == False:
            savable = False

        return savable

    def check_instance_deployable(self, working_platform: Instance) -> bool:
        return True if self.check_instance_uncaught(working_platform) == False and working_platform.new_instance == False else False

    def connection_validity(self, working_platform: Instance) -> tuple[bool, dict[str, bool]]:
        valid = True
        validity_map: dict[str, bool] = {
            "id" : True,
            "ansible_user" : True,
            "ansible_host" : True,
            "ansible_port" : True,
            "http_proxy" : True,
            "https_proxy" : True,
            "volttron_venv" : True,
            "volttron_home" : True
        }

        # Check if this is a local connection
        is_local = working_platform.host.ansible_connection == "local"

        # Validate the host id
        if working_platform.host.id == "":
            valid = False
            validity_map["id"] = False

        # Validate the ansible user
        if working_platform.host.ansible_user == "":
            valid = False
            validity_map["ansible_user"] = False

        # Validate the ansible host
        if working_platform.host.ansible_host == "":
            valid = False
            validity_map["ansible_host"] = False

        # Validate the ansible port (only for SSH connections)
        if not is_local:
            if not isinstance(working_platform.host.ansible_port, int):
                if not working_platform.host.ansible_port.isnumeric():
                    valid = False
                    validity_map["ansible_port"] = False

        return (valid, validity_map)

    def platform_validity(self, working_platform: Instance) -> tuple[bool, dict[str, bool]]:
        valid = True
        validity_map: dict[str, bool] = {
            "instance_name" : True,
            "instance_name_not_used" : True,
            "vip_address" : True
        }
        # Validate the instance name
        valid_field_name_for_instance = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-/-]*$")
        if not valid_field_name_for_instance.fullmatch(working_platform.platform.config.instance_name):
            valid = False
            validity_map["instance_name"] = False

        new_name = working_platform.platform.config.instance_name
        existing_names=[p.platform.safe_platform["config"]["instance_name"] for p in self.in_file_platforms if p.new_instance == False and self.current_uid != p.platform.safe_platform["config"]["instance_name"]]

        # Check to see if our instance is taken already:
        # Seeing if our instance name is inside a list of already registered instance names...
        if working_platform.platform.config.instance_name in [p.platform.safe_platform["config"]["instance_name"] for p in self.in_file_platforms if p.new_instance == False and self.current_uid != p.platform.safe_platform["config"]["instance_name"]]:
            valid = False
            validity_map["instance_name_not_used"] = False


        # Validate the tcp address
        if not re.match(r'^tcp://[\d.]+:\d+$', working_platform.platform.config.vip_address):
            valid = False
            validity_map["vip_address"] = False

        return (valid, validity_map)