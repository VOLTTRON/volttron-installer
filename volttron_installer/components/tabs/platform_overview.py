import reflex as rx
from ...pages.platform_page import State as PlatformState
from ...models import InstanceStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import Instance


def platform_row(platform_entry: "Instance") -> rx.Component:
    """Single row in the platforms table - Docker Desktop style"""
    
    # Determine status display based on status field
    is_loading = platform_entry.status == InstanceStatus.LOADING.value
    is_deployed = platform_entry.status == InstanceStatus.DEPLOYED.value
    is_error = platform_entry.status == InstanceStatus.ERROR.value
    
    return rx.table.row(
        # Status dot + Name (clickable link)
        rx.table.cell(
            rx.link(
                rx.hstack(
                    rx.cond(
                        is_loading,
                        rx.spinner(size="1", color="gray"),
                        rx.box(
                            width="8px",
                            height="8px",
                            border_radius="50%",
                            background=rx.cond(
                                is_error,
                                "var(--red-9)",
                                rx.cond(
                                    is_deployed,
                                    "var(--green-9)",
                                    "var(--gray-8)"
                                )
                            ),
                        ),
                    ),
                    rx.text(
                        platform_entry.platform.config.instance_name,
                        weight="medium"
                    ),
                    spacing="2",
                    align="center"
                ),
                href=f"/platform/{platform_entry.platform.config.instance_name}",
            )
        ),
        # Host IP
        rx.table.cell(
            rx.text(platform_entry.host.ansible_host, size="2", color="gray")
        ),
        # SSH User
        rx.table.cell(
            rx.text(platform_entry.host.ansible_user, size="2", color="gray")
        ),
        # Agent count
        rx.table.cell(
            rx.text(platform_entry.platform.agents.length(), size="2", color="gray")
        ),
        # Status badge
        rx.table.cell(
            rx.cond(
                is_loading,
                rx.badge("Loading...", color_scheme="gray", size="1"),
                rx.cond(
                    is_error,
                    rx.badge("Error", color_scheme="red", size="1"),
                    rx.badge(
                        rx.cond(is_deployed, "Deployed", "Not Deployed"),
                        color_scheme=rx.cond(is_deployed, "green", "gray"),
                        size="1"
                    )
                )
            )
        ),
        # Actions menu
        rx.table.cell(
            rx.menu.root(
                rx.menu.trigger(
                    rx.icon_button(
                        rx.icon("more-vertical", size=16),
                        variant="ghost",
                        size="1"
                    )
                ),
                rx.menu.content(
                    rx.menu.item(
                        "Copy",
                        on_click=PlatformState.copy_platform(
                            platform_entry.platform.config.instance_name
                        )
                    ),
                    rx.menu.item(
                        "Delete",
                        color="red",
                        on_click=PlatformState.delete_platform_instant(
                            platform_entry.platform.config.instance_name
                        )
                    )
                )
            )
        ),
        _hover={"background": "var(--gray-3)"},
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
                    PlatformState.in_file_platforms,
                    platform_row
                )
            ),
            width="100%",
        ),
        padding="1rem",
        width="100%",
    )
