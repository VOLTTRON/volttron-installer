import reflex as rx
from ..form_components import *
from ..tabs.state import PlatformOverviewState, HostsTabState, PlatformState

def platform_config_form(platform_uid: str) -> rx.Component:

    return rx.cond(
        PlatformOverviewState.platforms.contains(platform_uid),
        form_view.form_view_wrapper(
            form_entry.form_entry(
                "Hosts",
                rx.select(
                    ["host1", "host2", "host3", "host4"],
                    name="select_host"
                )
            ),
            form_entry.form_entry(
                "Name",
                rx.text_field(
                    value=PlatformOverviewState.platforms[platform_uid]["name"],
                    # value=PlatformOverviewState.get_platform_field(platform_uid=platform_uid, field="name"),
                    on_change=lambda v: PlatformOverviewState.update_form_field(platform_uid, "name", v)
                )
            ),
            form_entry.form_entry(
                "Address",
                rx.text_field(
                    value=PlatformOverviewState.platforms[platform_uid]["address"],
                    on_change=lambda v: PlatformOverviewState.update_form_field(platform_uid, "address", v)
                )
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
                )
            ),
            form_entry.form_entry(
                "Added Agents",
                rx.button(
                    "Add an Agent"
                )
            ),
        ),
        rx.text("Platform not found")
    )