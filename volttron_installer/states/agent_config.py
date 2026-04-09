"""AgentConfigState - Agent configuration editing state."""

import reflex as rx
import json
import csv
import yaml
import re
import io
from loguru import logger
from typing import Any

from ..model_views import AgentModelView, ConfigStoreEntryModelView
from ..models import Instance
from ..utils.create_component_uid import generate_unique_uid
from ..utils.conversion_methods import json_string_to_csv_string, csv_string_to_usable_dict, identify_string_format, csv_string_to_json_string
from ..utils.validate_content import check_json, check_csv, check_path, check_yaml, check_regular_expression
from ..utils.create_csv_string import create_csv_string, create_and_validate_csv_string
from ..utils import delete_file
from ..navigation.state import NavigationState
from ..thin_endpoint_wrappers import get_vctl_config_list, get_vctl_config_get


class AgentConfigState(rx.State):
    working_agent: AgentModelView = AgentModelView()
    selected_component_id: str = ""
    draft_visible: bool = False

    # Vars
    # this being named agent details doesn't make sense to be honest
    @rx.var
    def agent_details(self) -> dict:
        args = self.router.page.params
        uid = args.get("uid", "")
        agent_uid = args.get("agent_uid", "")
        return {"uid": uid, "agent_uid": agent_uid}

    @rx.var
    def selected_tab(self) -> str:
        return self.working_agent.selected_agent_config_tab

    # ========= state vars to streamline working checking the validity of working config =======

    # TODO: implement def config_uncaught var
    @rx.var
    def path_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity_map["path"]
        return False

    @rx.var
    def config_json_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity_map["json"]
        return False

    @rx.var
    def check_csv_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity_map["csv"]
        return False

    @rx.var
    def working_csv_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                if i.data_type == "JSON":
                    return True
                # What we want to do here is to check if
                valid, csv_string = create_and_validate_csv_string(data_dict=i.csv_variants[i.selected_variant])
                # logger.debug(f"is our cworking csv valid?: {valid}")
                # logger.debug(f"this is our variant: {i.csv_variants[i.selected_variant]}")
                # logger.debug(f"this is our csv string: {csv_string}")
                if valid:
                    i.value = csv_string
                    return True
                return False
            return True
        return True

    @rx.var
    def entry_config_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity_map["config"]
        return False

    @rx.var
    def config_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity
        return False

    @rx.var
    def changed_configs_list(self) -> list[str]:
        """returns a list of component ids for the config store entries that have been changed"""
        return list(config.component_id for config in self.working_agent.config_store if config.dict() != config.safe_entry or config.safe_entry["path"] == "")

    @rx.var
    def committed_configs(self) -> list[ConfigStoreEntryModelView]:
        return [
            ConfigStoreEntryModelView(
                    path=config.safe_entry["path"],
                    data_type=config.safe_entry["data_type"],
                    value=config.safe_entry["value"],
                    csv_variants=config.csv_variants,
                    component_id=config.component_id,
                    selected_variant=config.selected_variant,
                ) for config in self.working_agent.config_store if not config.uncommitted]

    @rx.var
    def has_valid_configs(self) -> bool:
        return (len(self.working_agent.config_store) > 0 and
                any(not config.uncommitted for config in self.working_agent.config_store))

    @rx.var
    def num_of_new_invalid_configs(self) -> int:
        return len([config.path for config in self.working_agent.config_store if config.uncommitted])
    # ======== End of config validation vars =========


    # ======= state vars to streamline agent validation =======
    # Cache for validity check results to prevent redundant API calls
    _agent_validity_cache: dict[str, Any] = {}
    _agent_validity_cache_key: str = ""

    @rx.var
    async def agent_validity_status(self) -> dict[str, bool]:
        """Cached validity check - all other validity vars read from this"""
        # Create cache key from relevant fields
        cache_key = f"{self.agent_details.get('uid', '')}:{self.working_agent.identity}:{self.working_agent.source}:{self.working_agent.config}:{self.working_agent.routing_id}"

        # Return cached result if key matches
        if cache_key == self._agent_validity_cache_key and self._agent_validity_cache:
            return self._agent_validity_cache

        # Compute fresh validity
        valid, validity_map = await self.check_agent_validity()
        validity_map["overall_valid"] = valid

        # Update cache
        self._agent_validity_cache = validity_map
        self._agent_validity_cache_key = cache_key

        return validity_map

    @rx.var
    async def agent_valid(self) -> bool:
        """checks if the agent identity is valid"""
        validity = await self.agent_validity_status
        return validity.get("overall_valid", False)

    @rx.var
    async def agent_identity_not_in_use(self) -> bool:
        """checks if the agent identity is valid"""
        validity = await self.agent_validity_status
        return validity.get("identity_not_in_use", False)

    @rx.var
    async def agent_identity_validity(self) -> bool:
        """checks if the agent identity is valid"""
        validity = await self.agent_validity_status
        return validity.get("identity_valid", False)

    @rx.var
    async def agent_source_validity(self) -> bool:
        """checks if the agent source is valid"""
        validity = await self.agent_validity_status
        return validity.get("source", False)

    @rx.var
    async def agent_config_validity(self) -> bool:
        """checks if the agent config is valid"""
        validity = await self.agent_validity_status
        return validity.get("config", False)

    # ======== End of agent validation vars========

    # Events
    async def _load_live_agent_config_store(self, platform_uid: str, agent_identity: str) -> tuple[str, list[ConfigStoreEntryModelView]]:
        """Fetch config store entries from live vctl data for a given agent.

        Returns (resolved_identity, entries). If no identity resolves, returns ("", []).
        """
        identity_candidates: list[str] = []
        for candidate in [
            agent_identity,
            agent_identity.replace("-", "."),
            agent_identity.replace(".", "-"),
        ]:
            candidate = candidate.strip()
            if candidate and candidate not in identity_candidates:
                identity_candidates.append(candidate)

        for candidate in identity_candidates:
            try:
                response = await get_vctl_config_list(platform_uid, candidate)
                data = response.json() if hasattr(response, "json") else response
                keys = data.get("entries", [])

                entries: list[ConfigStoreEntryModelView] = []
                for key in keys:
                    get_response = await get_vctl_config_get(platform_uid, candidate, key)
                    get_data = get_response.json() if hasattr(get_response, "json") else get_response
                    content = str(get_data.get("content", ""))
                    data_type = "JSON" if check_json(content) else "CSV"

                    config_entry = ConfigStoreEntryModelView(
                        path=key,
                        data_type=data_type,
                        value=content,
                        uncommitted=False,
                        component_id=generate_unique_uid(),
                        safe_entry={
                            "path": key,
                            "data_type": data_type,
                            "value": content,
                        },
                    )

                    if data_type == "CSV":
                        try:
                            config_entry.csv_variants["Custom"] = csv_string_to_usable_dict(content)
                        except Exception:
                            pass

                    entries.append(config_entry)

                return candidate, entries
            except Exception:
                continue

        return "", []

    @rx.event
    async def hydrate_working_agent(self):
        """Initialize working agent from platform state"""
        from ..state import PlatformPageState
        platform_state: PlatformPageState = await self.get_state(PlatformPageState)
        uid = self.agent_details["uid"]
        agent_uid = self.agent_details["agent_uid"]

        if uid not in platform_state.platforms:
            return

        working_platform: Instance = platform_state.platforms[uid]
        normalized_target = agent_uid.replace("-", ".")

        # Primary match against persisted platform agents.
        for agent in working_platform.platform.agents.values():
            if (
                agent.routing_id == agent_uid
                or agent.identity == agent_uid
                or agent.routing_id == normalized_target
                or agent.identity == normalized_target
            ):
                self.working_agent = agent
                resolved_identity, live_entries = await self._load_live_agent_config_store(uid, agent.identity)
                if resolved_identity:
                    self.working_agent.config_store = live_entries
                else:
                    yield rx.toast.warning(
                        "Unable to read live config store via vctl. Start the platform and refresh status, then try again."
                    )
                return

        # Fallback for agents discovered from live runtime status but not yet persisted.
        live_agents = platform_state._platform_status.get("agents", {})
        for live_key, live_data in live_agents.items():
            live_identity = str(live_data.get("identity", "") or live_key)
            live_uuid = str(live_data.get("uuid", "") or "")
            if agent_uid in (str(live_key), live_identity, live_uuid):
                self.working_agent = AgentModelView(
                    identity=live_identity,
                    source=live_identity,
                    config="{}",
                    config_store=[],
                    routing_id=live_identity,
                    is_new=False,
                    config_store_allowed=True,
                    safe_agent={
                        "identity": live_identity,
                        "source": live_identity,
                        "config": "{}",
                        "config_store": {},
                    },
                )
                resolved_identity, live_entries = await self._load_live_agent_config_store(uid, live_identity)
                if resolved_identity:
                    self.working_agent.config_store = live_entries
                else:
                    yield rx.toast.warning(
                        "Unable to read live config store via vctl. Start the platform and refresh status, then try again."
                    )
                return

    @rx.event
    def change_agent_config_tab(self, value):
        self.working_agent.selected_agent_config_tab = value

    @rx.event
    def flip_draft_visibility(self):
        self.draft_visible = not self.draft_visible
        logger.debug(f"ok bro is {self.draft_visible}")
        logger.debug(f"this is our working agent config store: {self.working_agent.config_store}")
        logger.debug(f"committed configs in agent config store: {self.committed_configs}")

    @rx.event
    async def update_agent_detail(self, field: str, value: str, id: str = None):
        """Update agent details directly"""
        setattr(self.working_agent, field, value)

        if id is not None:
            yield rx.set_value(id, value)

        valid, validity_map = await self.check_agent_validity()
        self.working_agent.contains_errors = not valid

    @rx.event
    async def update_config_detail(self, field: str, value: str, id: str = None):
        """Update a config store entry directly"""
        for config in self.working_agent.config_store:
            # get the working config
            if config.component_id == self.working_agent.selected_config_component_id:
                logger.debug("updating details...")

                if field == "data_type":
                    # if the config value is nothing, just let them change the data type mannn
                    if config.value == "":
                        setattr(config, field, value)
                    else:
                        # method to convert if json to csv and vice versa
                        format =  identify_string_format(config.value)
                        # Means we are switching from CSV -> JSON
                        if format == "CSV":
                            json_string =  csv_string_to_json_string(config.value)
                            setattr(config, field, value)
                            setattr(config, "value", json_string)
                        elif format == "JSON":
                            csv_string =  json_string_to_csv_string(config.value)
                            usable_csv =  csv_string_to_usable_dict(csv_string)
                            config.csv_variants["Custom"] = usable_csv
                            setattr(config, field, value)
                else:
                    setattr(config, field, value)
                valid, valid_map = self.check_entry_validity(config)
                logger.debug(f"this is the validity map: {valid_map}")
                config.valid = valid
                config.changed = config.dict() != config.safe_entry
                if id is not None:
                    yield rx.set_value(id, value)
                break

    @rx.event
    def handle_unsaved_config_banner_click(self, component_id: str):
        """Handle click on unsaved config banner to set the selected component id"""
        self.working_agent.selected_config_component_id = component_id
        yield AgentConfigState.flip_draft_visibility
        yield AgentConfigState.change_agent_config_tab("2")

    @rx.event
    async def handle_config_store_entry_upload(self, files: list[rx.UploadFile]):
        # dealing with file uploads
        current_file = files[0]
        upload_data = await current_file.read()
        outfile = (rx.get_upload_dir() / current_file.name)

        with outfile.open("wb") as file_object:
            file_object.write(upload_data)

        result: str = ""
        file_type: str = ""

        if current_file.name.endswith('.json'):
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                file_type = "JSON"
                result = json.dumps(data, indent=4)

        elif current_file.name.endswith('.csv'):
            with open(outfile, 'r') as file_object:
                reader = csv.reader(file_object)
                output = io.StringIO()
                writer = csv.writer(output)
                for row in reader:
                    writer.writerow(row)
                file_type="CSV"
                result = output.getvalue()
                output.close()
        else:
            yield rx.toast.error("Unsupported file format")
            return

        # creating a model view from our uploaded config
        agent = self.working_agent
        new_config_entry= ConfigStoreEntryModelView(
                path="",
                data_type=file_type,
                value=result,
                component_id=generate_unique_uid()
            )
        if file_type == "CSV":
            usable_csv = csv_string_to_usable_dict(result)
            logger.debug(f"this is the usable? csv: {usable_csv}")
            new_config_entry.csv_variants["Custom"] = usable_csv
            logger.debug(f"this is out variants: {new_config_entry.csv_variants}")

        new_config_entry.safe_entry=new_config_entry.dict()
        logger.debug(f"I submitted a safe entry: {new_config_entry.safe_entry}")
        logger.debug(f"pls add: {new_config_entry.component_id}")
        agent.config_store.append(
            new_config_entry
        )
        logger.debug("agent config store entry was uploaded")
        yield AgentConfigState.set_component_id(new_config_entry.component_id)
        yield rx.toast.success("Config store entry uploaded successfully")
        delete_file.delete_file(current_file.name)

    @rx.event
    async def handle_agent_config_upload(self, files: list[rx.UploadFile]):
        file = files[0]
        upload_data = await file.read()
        outfile = (rx.get_upload_dir() / file.name)

        with outfile.open("wb") as file_object:
            file_object.write(upload_data)

        result: str = ""

        if file.name.endswith('.json'):
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                result = json.dumps(data, indent=4)
        elif file.name.endswith('.yaml') or file.name.endswith('.yml'):
            with open(outfile, 'r') as file_object:
                data = yaml.safe_load(file_object)
                result = yaml.dump(data, sort_keys=False, default_flow_style=False)
        else:
            yield rx.toast.error("Unsupported file format")
            return

        agent = self.working_agent
        agent.config = result
        yield rx.set_value("agent_config_field", result)
        delete_file.delete_file(file.name)

    @rx.event
    def create_blank_config_entry(self):
        agent = self.working_agent
        new_component_id = generate_unique_uid()
        blank_config = ConfigStoreEntryModelView(
                path="",
                data_type="JSON",
                value="",
                component_id=new_component_id,
                safe_entry={
                    "path" : "",
                    "data_type" : "JSON",
                    "value" : ""
                }
            )
        blank_config.safe_entry = blank_config.dict()
        agent.config_store.append(blank_config)
        yield AgentConfigState.set_component_id(new_component_id)

    @rx.event
    def save_config_store_entry(self, config: ConfigStoreEntryModelView):
        # Keep a variable so we can stack the toast errors if config entry has many errors, instead of ending
        # the function at just one error
        import re
        committable: bool = True

        logger.debug(f"this is our config's safe entry: {[entry.safe_entry for entry in self.working_agent.config_store]}")
        list_of_config_paths: list[tuple[str, str]] = [
            (entry.safe_entry["path"], entry.component_id) for entry in self.working_agent.config_store
        ]
        logger.debug(f"list of config paths: {list_of_config_paths}")

        # Check if the path exists and belongs to a different component
        for path, component_id in list_of_config_paths:
            if config.path == "" or (config.path == path and config.component_id != component_id):
                # This check catches all empty paths or duplicate paths
                committable = False
                yield rx.toast.error(f"Config path is already in use.")

        # Validate the path format using a stricter regex pattern
        # valid_field_name_for_config_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
        # if not valid_field_name_for_config_pattern.fullmatch(config.path):
        #     committable = False
        #     yield rx.toast.error("Path must start with a letter and can only contain letters, numbers, underscores, or hyphens.")

        if config.data_type == "CSV" and committable:
            try:
                logger.debug(f"just for notes, here is thing: {config.csv_variants}")
                working_dict = config.csv_variants[config.selected_variant]
                headers=list(working_dict.keys())
                rows = [[working_dict[header] for header in headers] for i in range(10)]

                csv_string = create_csv_string(headers, rows)

                if not check_csv(csv_string):
                    raise ValueError("CSV String is not valid")

                config.csv_header_row=headers
                config.formatted_csv=rows
            except Exception as e:
                logger.debug(f"error: {e}")
                committable = False
                yield rx.toast.error("CSV variant is not valid")
            pass

        elif config.data_type =="JSON" and committable:
            if check_json(config.value) == False:
                committable = False
                yield rx.toast.error("Inputted JSON is not valid")

        if committable == False:
            return

        config.safe_entry = config.dict()
        config.uncommitted=False

        # Find and update the entry in the config_store just to be safe
        for i, entry in enumerate(self.working_agent.config_store):
            if entry.component_id == config.component_id:
                # logger.debug(f"ok first of all, uncommitted??: {self.working_agent.config_store[i].uncommitted}")
                self.working_agent.config_store[i] = config
                # logger.debug(f"updated entries committed state: {self.working_agent.config_store[i].uncommitted}")
                break

        # logger.debug(f"our agent after entry save: {self.working_agent}")
        return rx.toast.success("Config saved successfully")

    @rx.event
    def delete_config_store_entry(self, config: ConfigStoreEntryModelView):
        logger.debug(f"implement the rest of this, {config.component_id} was clicked for deletion")
        for index, entry in enumerate(self.working_agent.config_store):
            if entry.component_id == config.component_id:
                self.working_agent.config_store.pop(index)
                logger.debug(f"selected_component_id = {self.selected_component_id}, entry.component_id = {config.component_id}")
                if self.selected_component_id == config.component_id:
                    yield AgentConfigState.set_component_id("")
                yield rx.toast.info(f"Config store entry has been removed.")
                return

    @rx.event
    def text_editor_edit(self, config: ConfigStoreEntryModelView, value: str):
        logger.debug("im being ran right?")
        config.value = value
        config.valid = check_json(config.value)
        logger.debug(f"valid?: {config.valid}")
        logger.debug(f" bruhhh this odddeee: {self.has_valid_configs}")

    @rx.event
    async def save_agent_config(self):
        """Save agent configuration"""
        from ..state import PlatformPageState
        agent = self.working_agent
        # check if identity already exists:
        platform_state: PlatformPageState = await self.get_state(PlatformPageState)
        working_platform: Instance = platform_state.platforms[self.agent_details["uid"]]
        registered_identities: list[str] = [ i for i, a in working_platform.platform.agents.items() if a.routing_id != agent.routing_id]
        if agent.identity in registered_identities:
            yield AgentConfigState.flip_draft_visibility
            yield rx.toast.error("Identity is already in use!")
            return
        agent.is_new = False
        agent.safe_agent = agent.to_dict()

        # Work with our safe agent just to be safe
        # working_platform.platform.safe_platform["agents"][agent.safe_agent["identity"]] = agent.safe_agent
        logger.debug("oh yeah, we saved and here is our platform agents:")
        logger.debug(f"{working_platform.platform.agents}")
        yield AgentConfigState.flip_draft_visibility
        yield rx.toast.success("Agent configuration saved")

        # Go back to the platform:
        navigation_state = await self.get_state(NavigationState)
        yield navigation_state.route_back_to_platform(
            self.agent_details["uid"]
        )

    @rx.event
    def print_config_properties(self, config: ConfigStoreEntryModelView):
        unpacked = config.dict()
        logger.debug(f"here is my config: \n {unpacked}")
        logger.debug("this is a component id ")
        logger.debug(config.component_id)

    @rx.event
    def set_component_id(self, component_id: str):
        if self.working_agent.selected_config_component_id == component_id:
            self.working_agent.selected_config_component_id = ""
        else:
            self.working_agent.selected_config_component_id = component_id
        logger.debug(f"our new config entry: {self.working_agent.selected_config_component_id}")

    async def check_agent_validity(self) -> tuple[bool, dict[str, bool]]:
        valid: bool = True
        validity_map: dict[str, bool] = {
            "identity_valid": True,
            "identity_not_in_use": True,
            "source": True,
            "config": True
        }

        from ..state import PlatformPageState
        platform_state: PlatformPageState = await self.get_state(PlatformPageState)
        if self.agent_details["uid"] == "":
            return (valid, validity_map)

        # Check if the platform still exists (may have been deleted)
        if self.agent_details["uid"] not in platform_state.platforms:
            return (valid, validity_map)

        working_platform: Instance = platform_state.platforms[self.agent_details["uid"]]



        # Create a dictionary mapping identities to routing IDs
        identity_to_rid = {identity: agent.routing_id
                        for identity, agent in working_platform.platform.agents.items()}

        # Check if the identity already exists
        if self.working_agent.identity in identity_to_rid:
            # Checking if the existing identity is not the same as the current agent's identity via routing id
            if self.working_agent.routing_id != identity_to_rid[self.working_agent.identity]:
                valid = False
                validity_map["identity_not_in_use"] = False

        # implement Source validity:
        if check_path(self.working_agent.source) == False:
            valid = False
            validity_map["source"] = False

        # implement Identity validity:
        if check_regular_expression(self.working_agent.identity) == False:
            valid = False
            validity_map["identity_valid"] = False

        # config validity:
        # verify if the config is valid json or yaml
        if check_json(self.working_agent.config) == False:
            if check_yaml(self.working_agent.config) == False or self.working_agent.config == "":
                validity_map["config"] = False
                valid = False

        return (valid, validity_map)

    def check_entry_validity(self, config: ConfigStoreEntryModelView) -> tuple[bool, dict[str, bool]]:
        """checks the validity of each field in the config. also checks the json/csv versions
        returns bool for overall validity, and dict containing fields with errors in a string bool value pair"""
        valid: bool = True
        config_fields: dict[str, bool] = {
            "path" : True,
            "csv" : True,
            "json" : True,
            "config": True
        }

        # Checking validity for each data type
        if config.data_type == "JSON":
            config_fields["json"] = check_json(config.value)
            if check_json(config.value) == False:
                valid = False
                config_fields["config"] = False

            # add a separate base case for if the json is just an empty string
            if config.value == "":
                valid=False
                # This will let the user just be able to switch to csv if its a new empty
                # config store entry
                config_fields["config"] = True
        else:
            # if else, we validate the csv_field
            try:
                # get selected variant and turn it into legible csv
                working_dict = config.csv_variants[config.selected_variant]
                headers=list(working_dict.keys())
                rows = [working_dict[header] for header in headers]

                csv_string = create_csv_string(headers, rows)
                if check_csv(csv_string):
                    raise ValueError()

            except Exception as e:
                valid = False
                config_fields["csv"] = False
                config_fields["config"] = False
                logger.debug(f"the working csv field is not valid")

        # Validate the path format to include periods
        valid_field_name_for_config_path = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-/-]*$")
        if not valid_field_name_for_config_path.fullmatch(config.path):
            valid = False
            config_fields["path"] = False

        if self.working_csv_validity == False:
            valid = False
            config_fields["csv"] = False

        return (valid, config_fields)