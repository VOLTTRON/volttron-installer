import reflex as rx
from ...state import PlatformPageState as State

def install_agent_dialog() -> rx.Component:
    """Dialog for installing an agent on a running platform."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Install Agent"),
                rx.dialog.description(
                    "Install a new agent on the running VOLTTRON platform.",
                    size="2",
                ),
                # Mode toggle
                rx.hstack(
                    rx.button(
                        "From Catalog",
                        on_click=lambda: State.set_install_agent_mode("catalog"),
                        variant=rx.cond(State.install_agent_mode == "catalog", "solid", "soft"),
                        color_scheme=rx.cond(State.install_agent_mode == "catalog", "blue", "gray"),
                        size="2",
                    ),
                    rx.button(
                        "Manual",
                        on_click=lambda: State.set_install_agent_mode("manual"),
                        variant=rx.cond(State.install_agent_mode == "manual", "solid", "soft"),
                        color_scheme=rx.cond(State.install_agent_mode == "manual", "blue", "gray"),
                        size="2",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.divider(),
                # Catalog vs manual content
                rx.cond(
                    State.install_agent_mode == "catalog",
                    rx.vstack(
                        rx.text("Select an agent to install:", size="2", weight="bold"),
                        rx.box(
                            rx.vstack(
                                rx.foreach(
                                    State.list_of_agents,
                                    lambda agent: rx.box(
                                        rx.card(
                                            rx.flex(
                                                rx.flex(
                                                    rx.text(agent.identity, weight="bold", size="3"),
                                                    rx.text(agent.source, size="2", color="gray"),
                                                    direction="column",
                                                    spacing="1",
                                                    align="start",
                                                    flex="1",
                                                ),
                                                rx.cond(
                                                    State.selected_catalog_agent == agent.identity,
                                                    rx.icon("check", size=20, color="green"),
                                                    rx.box(width="20px", height="20px"),
                                                ),
                                                justify="between",
                                                align="center",
                                                width="100%",
                                                gap="3",
                                            ),
                                            width="100%",
                                            variant=rx.cond(
                                                State.selected_catalog_agent == agent.identity,
                                                "surface",
                                                "ghost"
                                            ),
                                        ),
                                        on_click=State.select_catalog_agent(agent.identity),
                                        width="100%",
                                        style={
                                            "cursor": "pointer",
                                        },
                                    ),
                                ),
                                spacing="2",
                                width="100%",
                            ),
                            width="100%",
                            max_height="400px",
                            overflow_y="auto",
                            padding="0.5rem",
                            overflow_x="hidden",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.vstack(
                            rx.text("Agent Identity", size="2", weight="bold"),
                            rx.input(
                                placeholder="e.g., listener",
                                value=State.install_agent_identity,
                                on_change=State.set_install_agent_identity,
                                width="100%",
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.text("Agent Source", size="2", weight="bold"),
                            rx.input(
                                placeholder="e.g., volttron-listener, path/to/agent.whl, or github:org/repo",
                                value=State.install_agent_source,
                                on_change=State.set_install_agent_source,
                                width="100%",
                            ),
                            rx.text(
                                "Package name, path to wheel file, or GitHub repository (github:org/repo)",
                                size="1",
                                color="gray",
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                ),
                # Start agent checkbox (common to both modes)
                rx.checkbox(
                    "Start agent after installation",
                    checked=State.install_agent_start,
                    on_change=State.set_install_agent_start,
                ),
                # Action buttons
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                        ),
                    ),
                    rx.button(
                        "Install",
                        on_click=State.handle_install_agent,
                        loading=State.installing_agent,
                        disabled=~State.can_install_agent,
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px",
        ),
        open=State.show_install_agent_dialog,
        on_open_change=State.close_install_agent_dialog,
    )
