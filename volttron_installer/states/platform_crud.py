"""PlatformCrudState - Hydration, CRUD operations, and agent add/remove for platforms."""

import reflex as rx
import json
import asyncio
import string
import random
from loguru import logger

from ..models import Instance, InstanceStatus
from ..model_views import AgentModelView, ConfigStoreEntryModelView, HostEntryModelView, PlatformModelView, PlatformConfigModelView
from ..utils.create_component_uid import generate_unique_uid
from ..utils.conversion_methods import csv_string_to_usable_dict
from ..utils.validate_content import check_json
from ..utils.prettify import prettify_json
from ..navigation.state import NavigationState
from ..backend.models import AgentType, HostEntry, PlatformConfig, PlatformDefinition, ConfigStoreEntry, AgentDefinition, CreatePlatformRequest, CreateOrUpdateHostEntryRequest
from ..thin_endpoint_wrappers import get_agent_catalog, get_all_platforms, get_hosts

from .driver_management import DriverManagementState
from ._hydration import __agents_off_catalog__, __instances_from_api__


class PlatformCrudState(DriverManagementState):
    # Left-sidebar nav selection
    platform_nav: str = "overview"

    @rx.event
    def set_platform_nav(self, section: str):
        self.platform_nav = section

    def generate_unique_uid(self, length=7) -> str:
        """Generate a short unique identifier that doesn't collide with existing platform UIDs."""
        characters = string.ascii_letters + string.digits
        while True:
            new_uid = ''.join(random.choice(characters) for _ in range(length))
            if new_uid not in self.platforms:
                return new_uid

    @rx.event
    async def hydrate_state(self, force_hydration: bool = False):
        if self.session_hydrated == False or force_hydration:
            # Make sure we have a valid 'blank' agent
            blank_agent = AgentModelView(
                    safe_agent={
                        "identity" : "",
                        "source" : "",
                        "config" : "",
                        "config_store": {}
                    },
                )

            # Collect async results into local variables first
            agent_list = await __agents_off_catalog__()
            platforms_from_api = await __instances_from_api__()

            # Append blank agent to the local list before assigning to state
            # (mutating self.list_of_agents directly after an await fails in background tasks)
            agent_list.append(blank_agent)
            self.list_of_agents = agent_list

            # Replace platforms entirely instead of updating to prevent deleted items from reappearing
            # Note: .update() on a StateProxy dict triggers _mark_dirty and raises ImmutableStateError
            # after an await, so we always do a direct assignment.
            if force_hydration:
                self.platforms = platforms_from_api
            else:
                self.platforms = {**self.platforms, **platforms_from_api}

            self.session_hydrated = True

            # Fetch statuses asynchronously in the background
            return PlatformCrudState.fetch_statuses_async

    @rx.event(background=True)
    async def fetch_statuses_async(self):
        """Fetch deployment status for all instances asynchronously."""
        async with self:
            instance_names = list(self.platforms.keys())

        logger.info(f"[STATUS_FETCH] Starting async status fetch for {len(instance_names)} instances")

        # Build a map of statuses
        status_map: dict[str, str] = {}
        for instance_name in instance_names:
            try:
                async with self:
                    if instance_name in self.platforms:
                        instance = self.platforms[instance_name]
                        if instance.deployed:
                            status_map[instance_name] = InstanceStatus.DEPLOYED.value
                        else:
                            status_map[instance_name] = InstanceStatus.NOT_DEPLOYED.value
            except Exception as e:
                logger.error(f"[STATUS_FETCH] Failed to fetch status for {instance_name}: {e}")
                status_map[instance_name] = InstanceStatus.ERROR.value

        # Apply all statuses and reassign to trigger Reflex reactivity
        async with self:
            for instance_name, status in status_map.items():
                if instance_name in self.platforms:
                    self.platforms[instance_name].status = status
            # Reassign to trigger UI update
            self.platforms = dict(self.platforms)

        logger.info("[STATUS_FETCH] Completed async status fetch")

    @rx.event
    def copy_platform(self, instance_name: str):
        from copy import deepcopy
        uid = self.generate_unique_uid()
        copy_instance = deepcopy(self.platforms[instance_name])
        copy_instance.platform.config.instance_name = uid
        copy_instance.refresh_for_copy()
        self.platforms[uid] = copy_instance
        self.current_uid = self.platforms[uid].platform.config.instance_name
        yield NavigationState.route_to_platform(self.platforms[uid].platform.config.instance_name)
        yield rx.toast.info(f"Platform: {instance_name} has been copied")
        # This is a weird way of doing it but we are doing this because
        # the UI routes to the instance name of a platform. and when we change
        # the instance name after we route to the uid it solves some headaches,
        # but probably should fix the headaches that it would cause.
        copy_instance.platform.config.instance_name = instance_name
        # yield self.update_platform_config_detail("instance_name", instance_name)

    @rx.event(background=True)
    async def delete_temp_uid(self, uid_copy: str):
        import asyncio
        await asyncio.sleep(5)  # Wait for 5 seconds (adjust as needed)
        async with self:
            self.platforms = {k: v for k, v in self.platforms.items() if k != uid_copy}
        logger.debug(f"this is the list of param afters: {list(self.platforms.keys())}")

    @rx.event
    def handle_adding_agent(self, agent: AgentModelView, uid: str):
        if uid not in self.platforms:
            return
        working_platform = self.platforms[uid]

        # Take a copy of the agent we are adding and make sure we dont have an already existing agent of the same identity
        new_agent: AgentModelView = agent.copy()
        if new_agent.identity in working_platform.platform.agents:
            new_agent.identity = f"{new_agent.identity}_{len(list(working_platform.platform.agents.values()))}"

        # Set routing id
        new_agent.routing_id = new_agent.identity if new_agent.identity != "" else generate_unique_uid()

        logger.debug("im going to add new component ids for config store...")
        # go through the config store, create new component ids for each config entry
        for i in new_agent.config_store:
            i.component_id = self.generate_unique_uid()
            logger.debug(f"added component uid: {i.component_id}")

        # Set up the safe agent for validation
        new_agent.safe_agent={
                    "identity": new_agent.identity,
                    "source": new_agent.source,
                    "config": new_agent.config,
                    "config_store" : agent.safe_agent["config_store"]
                }
        logger.debug(f"we added: {new_agent.identity}")
        logger.debug(f" and that safe config store is : {new_agent.safe_agent['config_store']}")
        # Prettify its config and config store contents:
        # loop through our agents one more time, and their config store. make if we
        # encounter a csv file, then we adjust the "Custom" CSV variant
        for config in new_agent.config_store:
            if config.data_type == "CSV":
                logger.debug(f"this is the config: {config}")
                usable_csv = csv_string_to_usable_dict(config.value)
                config.csv_variants["Custom"] = usable_csv
                logger.debug(f"this is the usable csv: {usable_csv}")
            elif config.data_type == "JSON":
                try:
                    json_data = json.loads(config.value)
                    pretty_json = json.dumps(json_data, indent=4)
                    config.value = pretty_json
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON: {e}")
                    pass

        # if config is json
        logger.debug(f"checking if valid json: {check_json(new_agent.config)}")
        pretty_json, success = prettify_json(new_agent.config)
        if success:
            new_agent.config = pretty_json
        for config in new_agent.config_store:
            # im kind of sick of all of this copy and pasting of block of code:
            # TODO find a better and safer way of doing this
            working_dict = config.csv_variants[config.selected_variant]
            config.csv_header_row = list(working_dict.keys())
            config.formatted_csv = [[working_dict[header] for header in config.csv_header_row] for i in range(10)]
            # ==============================================================
            config.safe_entry = config.dict()
            config.uncommitted = False
        working_platform.platform.agents[new_agent.identity] = new_agent
        yield rx.toast.info(f"{'A new agent' if new_agent.identity == '' else f'Agent {new_agent.identity}'} has been added")

    @rx.event
    def handle_removing_agent(self, identity: str):
        if self.current_uid not in self.platforms:
            return
        working_platform = self.platforms[self.current_uid]
        del(working_platform.platform.agents[identity])
        yield rx.toast.info(f"Agent '{identity}' has been removed")