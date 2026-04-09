"""Module-level helpers for hydrating platform and agent state from the backend API."""

import json
from loguru import logger

from ..utils.create_component_uid import generate_unique_uid
from ..utils.conversion_methods import csv_string_to_usable_dict
from ..utils.prettify import prettify_json
from ..model_views import AgentModelView, ConfigStoreEntryModelView, HostEntryModelView, PlatformModelView, PlatformConfigModelView
from ..models import Instance
from ..backend.models import AgentType, HostEntry, PlatformDefinition
from ..thin_endpoint_wrappers import get_agent_catalog, get_all_platforms, get_hosts


async def __agents_off_catalog__() -> list[AgentModelView]:
    catalog: dict[str, AgentType] = await get_agent_catalog()
    agent_list: list[AgentModelView] = []

    for identity, agent in catalog.items():
        agent_list.append(
            AgentModelView(
                identity=str(identity),
                routing_id=str(identity),
                source=agent.source,
                safe_agent={
                    "identity" : identity,
                    "source" : agent.source,
                    "config" : json.dumps(agent.default_config, indent=4),
                    "config_store" : {
                        path : {
                            "path" : path,
                            "data_type" : config.data_type,
                            "value" : config.value
                        }
                        for path, config in agent.default_config_store.items()
                    }
                },
                config_store_allowed = agent.config_store_allowed,
                config_store=[
                    ConfigStoreEntryModelView(
                        path=path,
                        data_type=entry.data_type,
                        value=str(entry.value),
                        uncommitted=False,
                        is_new=True,
                        safe_entry={
                            "path": path,
                            "data_type": entry.data_type,
                            "value": str(entry.value)
                        }
                    ) for path, entry in agent.default_config_store.items()
                ],
                config=json.dumps(agent.default_config, indent=4),
            )
        )
    return agent_list


async def __instances_from_api__() -> dict[str, Instance]:
    platforms: list[PlatformDefinition] = await get_all_platforms()
    hosts: list[HostEntry] = await get_hosts()
    host_by_id: dict[str, HostEntry] = {}
    for h in hosts:
        # Before we add to the map, lets clear None types for empty strings...
        # alternatively, we could use model_dump() and replace kv pairs with None types
        # to empty strings
        h = HostEntry(**h.to_dict())
        logger.info(f"[HYDRATE] Host loaded: id={h.id}, volttron_home={h.volttron_home}, volttron_venv={h.volttron_venv}")
        host_by_id[h.id] = h

    instances: dict[str, Instance] = {}

    # Creating platform model views, and instances
    for p in platforms:
        working_host_entry = host_by_id[p.host_id]
        host = HostEntryModelView(
            id=p.host_id,
            ansible_user=working_host_entry.ansible_user,
            ansible_host=working_host_entry.ansible_host,
            # For later type validation
            ansible_port=str(working_host_entry.ansible_port),
            ansible_connection=working_host_entry.ansible_connection,
            http_proxy=working_host_entry.http_proxy,
            https_proxy=working_host_entry.https_proxy,
            volttron_venv=working_host_entry.volttron_venv,
            volttron_home=working_host_entry.volttron_home,
            volttron_source=working_host_entry.volttron_source,
            host_configs_dir=working_host_entry.host_configs_dir,
            ignore_host_keys=working_host_entry.ignore_host_keys,
        )

        from ..models import InstanceStatus as _IS
        initial_status = _IS.DEPLOYED.value if p.deployed else _IS.NOT_DEPLOYED.value
        instance = {
            p.config.instance_name: Instance(
                host=host,
                platform=PlatformModelView(
                    in_file=True,
                    config=PlatformConfigModelView(
                        instance_name=p.config.instance_name,
                        vip_address=p.config.vip_address,
                        message_bus=p.config.message_bus,
                        volttron_type=p.config.volttron_type,
                        volttron_version=p.config.volttron_version,
                    ),
                    agents={
                        identity: AgentModelView(
                            identity=identity,
                            source=agent.source,
                            routing_id=identity,
                            safe_agent={
                                "identity" : identity,
                                "source" : agent.source,
                                "config": agent.config,
                            },
                            config_store_allowed=agent.config_store_allowed,
                            config_store=[
                                ConfigStoreEntryModelView(
                                    path=path,
                                    data_type=entry.data_type,
                                    value=str(entry.value),
                                    uncommitted=False,
                                    component_id=generate_unique_uid(),
                                    safe_entry={
                                        "path": path,
                                        "data_type": entry.data_type,
                                        "value": str(entry.value)
                                    },
                                ) for path, entry in agent.config_store.items()
                            ],
                            config="" if agent.config is None else prettify_json(agent.config)[0],
                        )
                        for identity, agent in p.agents.items()
                    }
                ),
                new_instance=False,
                deployed=p.deployed,
                status=initial_status,
                safe_host_entry=host.to_dict(),
            )
        }

        instances.update(instance)
    for uid, instance in instances.items():
        instance.platform.safe_platform = instance.platform.to_dict()
        for agent in instance.platform.agents.values():
            for config in agent.config_store:
                # Assign the config's safe_entry
                config.safe_entry = config.dict()
                if config.data_type == "CSV":
                    usable_csv = csv_string_to_usable_dict(config.value)
                    config.csv_variants["Custom"] = usable_csv
            # After going through the agent's config store and assigning the safe entries,
            # we can now assign the agent's safe_agent
            agent.safe_agent = agent.to_dict()

    return instances