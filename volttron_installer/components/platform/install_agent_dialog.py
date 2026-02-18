import reflex as rx
from ...state import PlatformPageState as State


def _github_offline_callout() -> rx.Component:
    """Shown in the catalog tab when GitHub is unreachable."""
    return rx.callout.root(
        rx.callout.icon(rx.icon("wifi-off")),
        rx.callout.text(
            rx.vstack(
                rx.text("Offline — Showing Built-in Catalog", weight="bold", size="2"),
                rx.text(
                    "Could not reach GitHub. Displaying the built-in modular agent catalog. "
                    "Check your network connection or add agents manually.",
                    size="2",
                ),
                spacing="1",
            )
        ),
        color="amber",
        variant="soft",
        width="100%",
    )


def _local_docs_callout() -> rx.Component:
    """Always shown at the top of the Local Agents tab — explains the expected structure."""
    return rx.callout.root(
        rx.callout.icon(rx.icon("info")),
        rx.callout.text(
            rx.vstack(
                rx.text("Local Agent Directory Structure", weight="bold", size="2"),
                rx.text(
                    "Place your custom agent in ~/volttron-workspace/ as a directory that contains a pyproject.toml:",
                    size="2",
                ),
                rx.box(
                    rx.code(
                        "~/volttron-workspace/",
                        display="block",
                    ),
                    rx.code(
                        "  your-agent-name/",
                        display="block",
                    ),
                    rx.code(
                        "    pyproject.toml    # name, description",
                        display="block",
                    ),
                    rx.code(
                        "    src/",
                        display="block",
                    ),
                    rx.code(
                        "    README.md",
                        display="block",
                    ),
                    background="var(--gray-a3)",
                    border_radius="4px",
                    padding="0.5rem",
                    font_size="0.75rem",
                    width="100%",
                ),
                rx.text(
                    "The agent will be installed from that directory path using pip.",
                    size="1",
                    color="gray",
                ),
                spacing="2",
            )
        ),
        color="gray",
        variant="soft",
        width="100%",
    )


def _agent_card(
    agent_identity: rx.Var,
    agent_source: rx.Var,
    is_selected: rx.Var,
    on_click_event,
) -> rx.Component:
    """Reusable selectable agent card."""
    return rx.box(
        rx.card(
            rx.flex(
                rx.flex(
                    rx.text(agent_identity, weight="bold", size="3"),
                    rx.text(agent_source, size="2", color="gray"),
                    direction="column",
                    spacing="1",
                    align="start",
                    flex="1",
                ),
                rx.cond(
                    is_selected,
                    rx.icon("check", size=20, color="green"),
                    rx.box(width="20px", height="20px"),
                ),
                justify="between",
                align="center",
                width="100%",
                gap="3",
            ),
            width="100%",
            variant=rx.cond(is_selected, "surface", "ghost"),
        ),
        on_click=on_click_event,
        width="100%",
        style={"cursor": "pointer"},
    )


def _catalog_mode_view() -> rx.Component:
    """Content for the 'From Catalog' tab — shows GitHub-fetched agents."""
    return rx.vstack(
        rx.cond(
            State.github_agents_offline,
            _github_offline_callout(),
            rx.box(),
        ),
        rx.cond(
            State.github_agents_loading,
            rx.center(
                rx.hstack(
                    rx.spinner(size="2"),
                    rx.text("Fetching agents from GitHub…", size="2", color="gray"),
                    spacing="2",
                    align="center",
                ),
                padding="2rem",
                width="100%",
            ),
            rx.box(
                rx.vstack(
                    rx.foreach(
                        rx.cond(
                            State.has_github_agents,
                            State.github_agents,
                            State.list_of_agents,
                        ),
                        lambda agent: _agent_card(
                            agent.identity,
                            agent.source,
                            State.selected_catalog_agent == agent.identity,
                            State.select_catalog_agent(agent.identity),
                        ),
                    ),
                    spacing="2",
                    width="100%",
                ),
                width="100%",
                max_height="340px",
                overflow_y="auto",
                padding="0.5rem",
                overflow_x="hidden",
            ),
        ),
        spacing="3",
        width="100%",
    )


def _local_mode_view() -> rx.Component:
    """Content for the 'Local Agents' tab — shows workspace agents + docs."""
    return rx.vstack(
        _local_docs_callout(),
        rx.cond(
            State.local_agents_loading,
            rx.center(
                rx.hstack(
                    rx.spinner(size="2"),
                    rx.text("Scanning ~/volttron-workspace…", size="2", color="gray"),
                    spacing="2",
                    align="center",
                ),
                padding="1rem",
                width="100%",
            ),
            rx.cond(
                State.has_local_agents,
                rx.box(
                    rx.vstack(
                        rx.foreach(
                            State.local_agents,
                            lambda agent: _agent_card(
                                agent.identity,
                                agent.local_path,
                                State.selected_local_agent == agent.identity,
                                State.select_local_agent(agent.identity),
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    width="100%",
                    max_height="240px",
                    overflow_y="auto",
                    padding="0.5rem",
                    overflow_x="hidden",
                ),
                rx.callout.root(
                    rx.callout.icon(rx.icon("folder-open")),
                    rx.callout.text("No agents found in ~/volttron-workspace. Add an agent directory there to get started."),
                    color="gray",
                    variant="soft",
                    width="100%",
                ),
            ),
        ),
        spacing="3",
        width="100%",
    )


def _manual_mode_view() -> rx.Component:
    """Content for the 'Manual' tab — custom identity and source entry."""
    return rx.vstack(
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
                placeholder="e.g., volttron-listener, /path/to/agent, or git+https://…",
                value=State.install_agent_source,
                on_change=State.set_install_agent_source,
                width="100%",
            ),
            rx.text(
                "PyPI package name, local directory path, or git URL",
                size="1",
                color="gray",
            ),
            spacing="2",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


def install_agent_dialog() -> rx.Component:
    """Dialog for installing an agent on a running VOLTTRON platform."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Install Agent"),
                rx.dialog.description(
                    "Install a new agent on the running VOLTTRON platform.",
                    size="2",
                ),
                # Three mode toggle buttons
                rx.hstack(
                    rx.button(
                        "From Catalog",
                        on_click=lambda: State.set_install_agent_mode("catalog"),
                        variant=rx.cond(State.install_agent_mode == "catalog", "solid", "soft"),
                        color_scheme=rx.cond(State.install_agent_mode == "catalog", "blue", "gray"),
                        size="2",
                    ),
                    rx.button(
                        "Local Agents",
                        on_click=lambda: State.set_install_agent_mode("local"),
                        variant=rx.cond(State.install_agent_mode == "local", "solid", "soft"),
                        color_scheme=rx.cond(State.install_agent_mode == "local", "blue", "gray"),
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
                # Tab content — nested rx.cond for three-way switch
                rx.cond(
                    State.install_agent_mode == "catalog",
                    _catalog_mode_view(),
                    rx.cond(
                        State.install_agent_mode == "local",
                        _local_mode_view(),
                        _manual_mode_view(),
                    ),
                ),
                # Start agent checkbox (shared across all modes)
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
            max_width="620px",
        ),
        open=State.show_install_agent_dialog,
        on_open_change=State.close_install_agent_dialog,
    )
