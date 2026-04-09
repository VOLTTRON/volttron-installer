import reflex as rx
from ...state import PlatformPageState as State
from ...navigation.state import NavigationState


def _connection_status_badge() -> rx.Component:
    return rx.tooltip(
        rx.badge(
            rx.hstack(
                rx.cond(
                    State.connection_status == "connected",
                    rx.cond(
                        State.is_local_connection,
                        rx.icon("monitor", size=15),
                        rx.icon("wifi", size=15),
                    ),
                    rx.cond(
                        State.connection_status == "checking",
                        rx.spinner(size="1"),
                        rx.cond(
                            State.is_local_connection,
                            rx.icon("monitor-x", size=15),
                            rx.icon("wifi-off", size=15),
                        ),
                    ),
                ),
                rx.text(
                    rx.cond(
                        State.connection_status == "connected",
                        rx.cond(State.is_local_connection, "Local Connected", "SSH Connected"),
                        rx.cond(
                            State.connection_status == "checking",
                            rx.cond(State.is_local_connection, "Checking Local...", "Checking SSH..."),
                            rx.cond(
                                State.connection_status == "disconnected",
                                rx.cond(State.is_local_connection, "Local Error", "SSH Disconnected"),
                                rx.cond(State.is_local_connection, "Local Unknown", "SSH Unknown"),
                            ),
                        ),
                    ),
                    size="3",
                ),
                spacing="2",
                align="center",
            ),
            color_scheme=rx.cond(
                State.connection_status == "connected",
                "green",
                rx.cond(State.connection_status == "checking", "blue", "red"),
            ),
            size="3",
        ),
        content=State.connection_tooltip,
    )


def _runtime_status_badge() -> rx.Component:
    return rx.badge(
        rx.hstack(
            rx.cond(
                State.starting_platform | State.stopping_platform | State.status_loading,
                rx.spinner(size="1"),
                rx.cond(
                    State.platform_state == "running",
                    rx.icon("circle-check", size=15),
                    rx.cond(
                        State.platform_state == "deployed",
                        rx.icon("circle-pause", size=15),
                        rx.icon("circle-x", size=15),
                    ),
                ),
            ),
            rx.text(
                rx.cond(
                    State.starting_platform,
                    "Starting VOLTTRON...",
                    rx.cond(
                        State.stopping_platform,
                        "Stopping VOLTTRON...",
                        rx.cond(
                            State.status_loading,
                            "Checking VOLTTRON...",
                            rx.cond(
                                State.platform_state == "running",
                                "VOLTTRON Running",
                                rx.cond(
                                    State.platform_state == "deployed",
                                    "VOLTTRON Stopped",
                                    rx.cond(
                                        State.platform_state == "not deployed",
                                        "Not Deployed",
                                        "VOLTTRON Unknown",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                size="3",
            ),
            spacing="2",
            align="center",
        ),
        color_scheme=rx.cond(
            State.starting_platform | State.stopping_platform | State.status_loading,
            "blue",
            rx.cond(
                State.platform_state == "running",
                "green",
                rx.cond(State.platform_state == "deployed", "orange", "gray"),
            ),
        ),
        size="3",
    )


def _connection_detail_badges() -> rx.Component:
    return rx.hstack(
        rx.cond(
            State.is_local_connection,
            rx.badge(
                rx.hstack(
                    rx.icon("monitor", size=12),
                    rx.text("Local Connection", size="2", weight="medium"),
                    spacing="1",
                    align="center",
                ),
                variant="soft",
                color_scheme="gray",
                size="2",
            ),
            rx.badge(
                rx.hstack(
                    rx.icon("terminal", size=12),
                    rx.text("SSH:", size="2", weight="medium"),
                    rx.text(
                        State.working_platform.host.ansible_user
                        + "@"
                        + State.working_platform.host.ansible_host
                        + ":"
                        + State.working_platform.host.ansible_port,
                        size="2",
                    ),
                    rx.icon("copy", size=12),
                    spacing="1",
                    align="center",
                ),
                variant="soft",
                color_scheme="gray",
                size="2",
                on_click=rx.call_script(
                    "navigator.clipboard.writeText('"
                    + "ssh -p "
                    + State.working_platform.host.ansible_port
                    + " "
                    + State.working_platform.host.ansible_user
                    + "@"
                    + State.working_platform.host.ansible_host
                    + "')"
                ),
                style={"cursor": "pointer"},
            ),
        ),
        rx.badge(
            rx.hstack(
                rx.icon("folder", size=12),
                rx.text("VOLTTRON_HOME:", size="2", weight="medium"),
                rx.text(State.effective_volttron_home, size="2"),
                rx.icon("copy", size=12),
                spacing="1",
                align="center",
            ),
            variant="soft",
            color_scheme="gray",
            size="2",
            on_click=rx.call_script(
                "navigator.clipboard.writeText('"
                + "export VOLTTRON_HOME="
                + State.effective_volttron_home
                + "')"
            ),
            style={"cursor": "pointer"},
        ),
        rx.badge(
            rx.hstack(
                rx.icon("box", size=12),
                rx.text("venv:", size="2", weight="medium"),
                rx.text(State.effective_volttron_venv, size="2"),
                rx.icon("copy", size=12),
                spacing="1",
                align="center",
            ),
            variant="soft",
            color_scheme="gray",
            size="2",
            on_click=rx.call_script(
                "navigator.clipboard.writeText('"
                + "source "
                + State.effective_volttron_venv
                + "/bin/activate"
                + "')"
            ),
            style={"cursor": "pointer"},
        ),
        spacing="2",
        wrap="wrap",
        width="100%",
    )


def _instance_information_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Platform Details", size="5"),
            rx.divider(),
            rx.grid(
                rx.vstack(
                    rx.text("Instance Name", size="3", weight="bold", color="gray"),
                    rx.text(State.platform_status.get("platform_id", "N/A"), size="4"),
                    align="start",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("State", size="3", weight="bold", color="gray"),
                    rx.badge(
                        State.platform_state,
                        color_scheme=rx.cond(
                            State.platform_state == "running",
                            "green",
                            rx.cond(State.platform_state == "deployed", "blue", "gray"),
                        ),
                        size="3",
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Host Configured", size="3", weight="bold", color="gray"),
                    rx.cond(
                        State.platform_status.get("host_configured", False),
                        rx.hstack(rx.icon("check", size=16, color="green"), rx.text("Yes", size="4"), spacing="2"),
                        rx.hstack(rx.icon("x", size=16, color="red"), rx.text("No", size="4"), spacing="2"),
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Keys Verified", size="3", weight="bold", color="gray"),
                    rx.cond(
                        State.is_local_connection,
                        rx.text("N/A (local)", size="4", color="gray"),
                        rx.cond(
                            State.platform_status.get("keys_verified", False),
                            rx.hstack(rx.icon("check", size=16, color="green"), rx.text("Yes", size="4"), spacing="2"),
                            rx.hstack(rx.icon("x", size=16, color="red"), rx.text("No", size="4"), spacing="2"),
                        ),
                    ),
                    align="start",
                    spacing="1",
                ),
                columns=rx.breakpoints(initial="1", sm="2", lg="4"),
                spacing="4",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
    )


def _agents_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.cond(
                State.agent_action_message != "",
                rx.callout(
                    State.agent_action_message,
                    icon="loader",
                    color_scheme="blue",
                ),
            ),
            rx.hstack(
                rx.vstack(
                    rx.heading("Agents", size="5"),
                    rx.text(
                        "Inspect runtime state and manage installed agents.",
                        size="2",
                        color="gray",
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.button(
                    rx.icon("plus", size=16),
                    "Add Agent",
                    on_click=State.open_install_agent_dialog,
                    size="3",
                    variant="soft",
                ),
                justify="between",
                align="start",
                width="100%",
                wrap="wrap",
                spacing="3",
            ),
            rx.divider(),
            rx.cond(
                State.platform_agents_list,
                rx.vstack(
                    rx.foreach(
                        State.platform_agents_list,
                        lambda agent: rx.card(
                            rx.hstack(
                                rx.vstack(
                                    rx.text(agent.get("name", ""), size="4", weight="medium"),
                                    rx.text(agent.get("identity", ""), size="2", color="gray"),
                                    spacing="1",
                                    align="start",
                                    min_width="220px",
                                ),
                                rx.hstack(
                                    rx.badge(
                                        agent.get("state", "unknown"),
                                        color_scheme=rx.cond(agent.get("state") == "running", "green", "gray"),
                                        size="2",
                                    ),
                                    rx.badge(
                                        rx.cond(agent.get("health", "") != "", agent.get("health", ""), "No health data"),
                                        color_scheme=rx.cond(agent.get("health", "") == "GOOD", "green", "gray"),
                                        variant="soft",
                                        size="2",
                                    ),
                                    spacing="2",
                                    wrap="wrap",
                                ),
                                rx.hstack(
                                    rx.cond(
                                        agent.get("state") != "running",
                                        rx.button(
                                            rx.icon("play", size=16),
                                            "Start",
                                            on_click=lambda: State.handle_start_agent(agent.get("uuid")),
                                            loading=State.starting_agent_uuid == agent.get("uuid"),
                                            size="2",
                                            variant="soft",
                                            color_scheme="green",
                                        ),
                                        rx.button(
                                            rx.icon("square", size=16),
                                            "Stop",
                                            on_click=lambda: State.handle_stop_agent(agent.get("uuid")),
                                            loading=State.stopping_agent_uuid == agent.get("uuid"),
                                            size="2",
                                            variant="soft",
                                            color_scheme="orange",
                                        ),
                                    ),
                                    rx.button(
                                        rx.icon("settings", size=16),
                                        "Configure",
                                        on_click=NavigationState.route_to_agent_config(
                                            State.current_uid,
                                            agent.get("id"),
                                        ),
                                        size="2",
                                        variant="ghost",
                                        color_scheme="gray",
                                    ),
                                    rx.button(
                                        rx.icon("trash-2", size=16),
                                        "Remove",
                                        on_click=lambda _, agent_uuid=agent.get("uuid"), agent_name=agent.get("name"): State.open_remove_agent_dialog(agent_uuid, agent_name),
                                        loading=State.removing_agent_uuid == agent.get("uuid"),
                                        size="2",
                                        variant="ghost",
                                        color_scheme="red",
                                        disabled=State.removing_agent_uuid != "",
                                    ),
                                    spacing="2",
                                    align="center",
                                    justify="end",
                                    wrap="wrap",
                                ),
                                justify="between",
                                align="center",
                                width="100%",
                                wrap="wrap",
                                spacing="3",
                            ),
                            width="100%",
                            variant="surface",
                        ),
                    ),
                    spacing="2",
                    width="100%",
                    align="stretch",
                ),
                rx.text("No agents installed. Click 'Add Agent' to install one.", size="4", color="gray"),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
    )


def _deployed_content() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header bar: title + primary runtime actions
            rx.hstack(
                rx.vstack(
                    rx.heading("Overview", size="7"),
                    rx.text(
                        "Monitor platform health, control runtime state, and manage installed agents.",
                        size="3",
                        color="gray",
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.hstack(
                    rx.cond(
                        State.platform_state == "running",
                        rx.button(
                            rx.icon("square", size=18),
                            "Stop Platform",
                            on_click=State.handle_stop_platform,
                            loading=State.stopping_platform,
                            disabled=State.status_loading | State.starting_platform,
                            size="3",
                            variant="soft",
                            color_scheme="red",
                        ),
                        rx.button(
                            rx.icon("play", size=18),
                            "Start Platform",
                            on_click=State.handle_start_platform,
                            loading=State.starting_platform,
                            size="3",
                            variant="soft",
                            color_scheme="green",
                            disabled=(State.platform_state == "not deployed") | State.status_loading | State.stopping_platform,
                        ),
                    ),
                    rx.button(
                        rx.icon("refresh-cw", size=18),
                        "Refresh",
                        on_click=State.refresh_platform_status,
                        loading=State.status_loading,
                        size="3",
                        variant="soft",
                    ),
                    spacing="2",
                    wrap="wrap",
                    justify="end",
                ),
                justify="between",
                align="end",
                wrap="wrap",
                width="100%",
                spacing="4",
            ),

            # Health strip: quick operational status at a glance
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.text("Runtime", size="2", color="gray", weight="medium"),
                        _runtime_status_badge(),
                        spacing="2",
                        align="start",
                        width="100%",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Connection", size="2", color="gray", weight="medium"),
                        _connection_status_badge(),
                        spacing="2",
                        align="start",
                        width="100%",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Host Configured", size="2", color="gray", weight="medium"),
                        rx.cond(
                            State.platform_status.get("host_configured", False),
                            rx.hstack(rx.icon("circle-check", size=16, color="var(--green-9)"), rx.text("Yes", size="3"), spacing="2"),
                            rx.hstack(rx.icon("circle-x", size=16, color="var(--red-9)"), rx.text("No", size="3"), spacing="2"),
                        ),
                        spacing="2",
                        align="start",
                        width="100%",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Last Updated", size="2", color="gray", weight="medium"),
                        rx.text(
                            rx.cond(State.last_status_check != "", State.last_status_check, "Not checked yet"),
                            size="3",
                        ),
                        rx.cond(
                            State.last_status_check_ago != "",
                            rx.text(State.last_status_check_ago, size="2", color="gray"),
                            rx.fragment(),
                        ),
                        spacing="2",
                        align="start",
                        width="100%",
                    ),
                    width="100%",
                ),
                columns=rx.breakpoints(initial="1", sm="2", xl="4"),
                spacing="3",
                width="100%",
            ),

            _agents_card(),

            # Secondary technical details
            rx.accordion.root(
                rx.accordion.item(
                    header=rx.hstack(
                        rx.icon("terminal", size=15, color="var(--gray-10)"),
                        rx.text("Connection & Paths", size="3", weight="medium"),
                        spacing="2",
                        align="center",
                    ),
                    value="details",
                    content=rx.vstack(
                        _connection_detail_badges(),
                        _instance_information_card(),
                        spacing="3",
                        width="100%",
                    ),
                ),
                type="single",
                collapsible=True,
                variant="soft",
                width="100%",
            ),

            rx.cond(
                State.status_error != "",
                rx.callout(
                    rx.hstack(
                        rx.icon("triangle_alert", size=16),
                        rx.text(State.status_error),
                        spacing="2",
                    ),
                    color_scheme="red",
                    width="100%",
                ),
            ),
            rx.cond(
                State.last_status_check != "",
                rx.text(f"Last runtime check: {State.last_status_check}", size="2", color="gray"),
            ),
            rx.moment(
                interval=15000,
                on_change=State.check_connection,
                display="none",
            ),
            rx.moment(
                interval=15000,
                on_change=State.refresh_platform_status,
                display="none",
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
        max_width="none",
        padding="1.5rem",
    )


def _not_deployed_content() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.icon("info", size=48, color="gray"),
            rx.heading("Platform Not Deployed", size="5"),
            rx.text(
                "Deploy this platform to view its status information.",
                size="3",
                color="gray",
            ),
            spacing="4",
            align="center",
            padding_top="4rem",
        ),
        width="100%",
        max_width="none",
        padding="1.5rem",
    )


def data_tab_content() -> rx.Component:
    return rx.cond(
        State.is_hydrated,
        rx.cond(State.platform_deployed, _deployed_content(), _not_deployed_content()),
    )
