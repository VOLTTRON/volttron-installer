import reflex as rx
from ..form_components import *
from ..tabs.state import PlatformOverviewState, HostsTabState, PlatformState, AgentSetupTabState

def platform_config_form(platform_uid: str) -> rx.Component:

    return rx.cond(
        PlatformOverviewState.platforms.contains(platform_uid),
        form_view.form_view_wrapper(
            form_entry.form_entry(
                "Hosts",
                rx.select.root(
                    rx.select.trigger(),
                    rx.select.content(
                        rx.select.group(
                            rx.foreach(
                                HostsTabState.committed_host_forms,
                                lambda x: rx.select.item(
                                    x[1]["host_id"], 
                                    value=x[1]["host_id"]
                                )
                            )
                        )
                    ),
                    name="select_host"
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Instance Name",
                rx.text_field(
                    value=PlatformOverviewState.platforms[platform_uid]["name"],
                    # value=PlatformOverviewState.get_platform_field(platform_uid=platform_uid, field="name"),
                    on_change=lambda v: PlatformOverviewState.update_form_field(platform_uid, "name", v)
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Vip Address",
                rx.text_field(
                    value=PlatformOverviewState.platforms[platform_uid]["address"],
                    on_change=lambda v: PlatformOverviewState.update_form_field(platform_uid, "address", v)
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Bus Type",
                rx.text("ZMQ")
            ),
            form_entry.form_entry(
                "Ports",
                rx.text_field(
                    value=PlatformOverviewState.platforms[platform_uid]["ports"],
                    on_change=lambda v: PlatformOverviewState.update_form_field(platform_uid, "ports", v)
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Added Agents",
                rx.select.root(
                    rx.select.trigger(),
                    rx.select.content(
                        rx.select.group(
                            rx.foreach(
                                AgentSetupTabState.committed_agent_forms,
                                lambda x: rx.select.item(
                                    x[1]["agent_name"], 
                                    value=x[1]["agent_name"]
                                )
                            )
                        )
                    ),
                    name="select_agents"
                )
            ),
        ),
        rx.text("Platform not found")
    )