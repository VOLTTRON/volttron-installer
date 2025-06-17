import reflex as rx
from ...state import IndexPageState, AppState

def sidebar_item(
    text: str, icon: str = False, width: str="100%", extra_style: dict={}, **props
) -> rx.Component:
    content = rx.hstack(
        rx.cond(
            icon,
            rx.icon(icon,  weight="medium", color="white"),
        ),
        rx.text(text, size="4", weight="medium", color="white"),
        width="100%",
        padding_x="0.5rem",
        padding_y="0.75rem",
        align="center",
        style={
            **extra_style,
            "_hover": {
                "bg": rx.color("accent", 4),
                "color": rx.color("accent", 11),
            },
            "border-radius": "0.5em",
        },
    )
    
    # If href is provided, use a link, otherwise use a button
    if "href" in props:
        return rx.link(
            content,
            weight="medium",
            width=width,
            **props
        )
    else:
        # Move on_click from props to button props if it exists
        on_click = props.pop("on_click", None)
        return rx.box(
            content,
            cursor="pointer",
            weight="medium",
            width=width,
            on_click=on_click,
            **props
        )

def sidebar_item_dropdown(
    text: str, *items, **props
) -> rx.Component:
    return rx.accordion.root(
        rx.accordion.item(
            rx.accordion.header(
                rx.accordion.trigger(        
                    rx.text(text, color="white", weight="medium"),
                    rx.cond(
                        AppState.tool_accordion_value == "tools",
                        rx.icon("chevron-up", color="white"),
                        rx.icon("chevron-down", color="white")
                    ),
                )
            ),
            rx.accordion.content(
                rx.vstack(
                    *items,
                    width="100%",
                )
            ),
            value="tools",
        ),
        value=AppState.tool_accordion_value,
        on_value_change=lambda value: AppState.toggle_tool_dropdown(value),
        collapsible=True,
        variant="ghost",
        style={"color" : "white", "border-radius": "0.5em"},
        width="100%",
    )


def sidebar_items() -> rx.Component:
    return rx.vstack(
        sidebar_item(
            text="Overview",
            icon="layout-dashboard",
            href="/",
            underline="none",
            on_click=lambda: AppState.select_overview,
            extra_style={
                "bg" : rx.cond(
                    AppState.sidebar_page_selected=="overview",
                    rx.color("accent", 4),
                    rx.color("accent", 3)
                )
            }
        ),
        sidebar_item_dropdown(
            "Tools",
            sidebar_item(
                "BACnet Scan",
                "search",
                underline="none",
                href="/tools/bacnet_scan",
                on_click=lambda: AppState.select_bacnet_scan,
                extra_style={
                "bg" : rx.cond(
                        AppState.sidebar_page_selected=="bacnet_scan",
                        rx.color("accent", 4),
                        rx.color("accent", 3)
                    )
                }
            ),
            on_click=AppState.toggle_tool_dropdown,
        ),
        spacing="1",
        width="100%",
    )

def app_sidebar() -> rx.Component:
    return rx.box(
        rx.desktop_only(
            rx.vstack(
                rx.hstack(
                    rx.image(
                        src="logo-mini.png",
                        width="2.25em",
                        height="auto",
                        border_radius="25%",
                    ),
                    rx.heading(
                        "VOLTTRON Installer", size="7", weight="bold"
                    ),
                    align="center",
                    justify="start",
                    padding_x="0.5rem",
                    width="100%",
                ),
                sidebar_items(),
                spacing="5",
                # position="fixed",
                # left="0px",
                # top="0px",
                # z_index="5",
                padding_x="1em",
                padding_y="1.5em",
                bg=rx.color("accent", 3),
                align="start",
                min_height="100%",
                height="100vh",
                width="16em",
            ),
        ),
        # rx.mobile_and_tablet(
        #     rx.drawer.root(
        #         rx.drawer.trigger(
        #             rx.icon("align-justify", size=30)
        #         ),
        #         rx.drawer.overlay(z_index="5"),
        #         rx.drawer.portal(
        #             rx.drawer.content(
        #                 rx.vstack(
        #                     rx.box(
        #                         rx.drawer.close(
        #                             rx.icon("x", size=30)
        #                         ),
        #                         width="100%",
        #                     ),
        #                     sidebar_items(),
        #                     spacing="5",
        #                     width="100%",
        #                 ),
        #                 top="auto",
        #                 right="auto",
        #                 height="100%",
        #                 width="20em",
        #                 padding="1.5em",
        #                 bg=rx.color("accent", 2),
        #             ),
        #             width="100%",
        #         ),
        #         direction="left",
        #     ),
        #     padding="1em",
        # ),
        height="100vh",  # Ensures the box takes full viewport height
        min_height="100%",  # Backup to ensure minimum height
    )