import reflex as rx
from ...pages.platform_page import State as PlatformState
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import Instance


def platform_row(platform_entry: "Instance") -> rx.Component:
    """Single row in the platforms table"""

    is_deployed = platform_entry.deployed
    is_local = platform_entry.host.ansible_connection == "local"

    connection_label = rx.cond(is_local, "Local", platform_entry.host.ansible_host)
    connection_icon = rx.cond(is_local, "monitor", "server")

    return rx.table.row(
        # Dot + Name
        rx.table.cell(
            rx.link(
                rx.hstack(
                    rx.box(
                        width="8px",
                        height="8px",
                        border_radius="50%",
                        flex_shrink="0",
                        background=rx.cond(is_deployed, "var(--green-9)", "var(--gray-6)"),
                    ),
                    rx.text(platform_entry.platform.config.instance_name, weight="medium", size="2"),
                    spacing="2",
                    align="center",
                ),
                href=f"/platform/{platform_entry.platform.config.instance_name}",
                color="inherit",
                text_decoration="none",
            )
        ),
        # Host / connection type
        rx.table.cell(
            rx.hstack(
                rx.icon(connection_icon, size=13, color="var(--gray-9)"),
                rx.text(connection_label, size="2", color="var(--gray-10)"),
                spacing="1",
                align="center",
            )
        ),
        # User (hidden for local)
        rx.table.cell(
            rx.cond(
                is_local,
                rx.text("—", size="2", color="var(--gray-7)"),
                rx.text(platform_entry.host.ansible_user, size="2", color="var(--gray-10)"),
            )
        ),
        # Agent count
        rx.table.cell(
            rx.text(platform_entry.platform.agents.length(), size="2", color="var(--gray-10)")
        ),
        # Status badge — simple, no spinner
        rx.table.cell(
            rx.badge(
                rx.cond(is_deployed, "Deployed", "Not Deployed"),
                color_scheme=rx.cond(is_deployed, "green", "gray"),
                variant="soft",
                size="1",
            )
        ),
        # Actions menu
        rx.table.cell(
            rx.menu.root(
                rx.menu.trigger(
                    rx.icon_button(
                        rx.icon("more-vertical", size=16),
                        variant="ghost",
                        size="1",
                    )
                ),
                rx.menu.content(
                    rx.menu.item(
                        "Copy",
                        on_click=PlatformState.copy_platform(
                            platform_entry.platform.config.instance_name
                        ),
                    ),
                    rx.menu.item(
                        "Delete",
                        color="red",
                        on_click=PlatformState.delete_platform_instant(
                            platform_entry.platform.config.instance_name
                        ),
                    ),
                ),
            )
        ),
        _hover={"background": "var(--gray-2)"},
    )


def platform_overview() -> rx.Component:
    """Main platform list - Docker Desktop style table"""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Name"),
                    rx.table.column_header_cell("Host"),
                    rx.table.column_header_cell("User"),
                    rx.table.column_header_cell("Agents"),
                    rx.table.column_header_cell("Status"),
                    rx.table.column_header_cell(""),
                )
            ),
            rx.table.body(
                rx.foreach(
                    PlatformState.in_file_platform_groups,
                    lambda device_group: rx.fragment(
                        rx.table.row(
                            rx.table.cell(
                                rx.hstack(
                                    rx.icon("server", size=14, color="var(--gray-9)"),
                                    rx.text(device_group.device_label, size="2", weight="bold"),
                                    rx.cond(
                                        device_group.ansible_user != "",
                                        rx.hstack(
                                            rx.text("(", size="1", color="var(--gray-10)"),
                                            rx.text(device_group.ansible_user, size="1", color="var(--gray-10)"),
                                            rx.text(")", size="1", color="var(--gray-10)"),
                                            spacing="0",
                                            align="center",
                                        ),
                                        rx.fragment(),
                                    ),
                                    rx.badge(
                                        device_group.instance_count,
                                        variant="soft",
                                        color_scheme="gray",
                                        size="1",
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                                col_span=6,
                                style={
                                    "background": "var(--gray-2)",
                                    "borderTop": "1px solid var(--gray-4)",
                                    "borderBottom": "1px solid var(--gray-4)",
                                },
                            ),
                        ),
                        rx.foreach(device_group.instances, platform_row),
                    ),
                )
            ),
            width="100%",
        ),
        padding="1rem",
        width="100%",
    )
