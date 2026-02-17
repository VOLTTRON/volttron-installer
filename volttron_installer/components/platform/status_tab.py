import reflex as rx
from ...state import PlatformPageState as State

def data_tab_content() -> rx.Component: 
    return rx.cond(
        State.is_hydrated,
        rx.cond(
            State.platform_deployed,
            # Show status information for deployed platforms
            rx.container(
                rx.vstack(
                    # Status Badges Row
                    rx.hstack(
                        # Connection Status Badge (adapts for local vs SSH)
                        rx.tooltip(
                            rx.badge(
                                rx.hstack(
                                    rx.cond(
                                        State.connection_status == "connected",
                                        rx.cond(
                                            State.is_local_connection,
                                            rx.icon("monitor", size=14),
                                            rx.icon("wifi", size=14),
                                        ),
                                        rx.cond(
                                            State.connection_status == "checking",
                                            rx.spinner(size="1"),
                                            rx.cond(
                                                State.is_local_connection,
                                                rx.icon("monitor-x", size=14),
                                                rx.icon("wifi-off", size=14),
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
                                                )
                                            )
                                        ),
                                        size="2",
                                    ),
                                    spacing="2",
                                ),
                                color_scheme=rx.cond(
                                    State.connection_status == "connected",
                                    "green",
                                    rx.cond(
                                        State.connection_status == "checking",
                                        "blue",
                                        "red"
                                    )
                                ),
                                size="2",
                            ),
                            content=State.connection_tooltip,
                        ),
                        # VOLTTRON Running Status Badge
                        rx.badge(
                            rx.hstack(
                                rx.cond(
                                    State.starting_platform | State.stopping_platform | State.status_loading,
                                    rx.spinner(size="1"),
                                    rx.cond(
                                        State.platform_state == "running",
                                        rx.icon("circle-check", size=14),
                                        rx.cond(
                                            State.platform_state == "deployed",
                                            rx.icon("circle-pause", size=14),
                                            rx.icon("circle-x", size=14),
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
                                                            "VOLTTRON Unknown"
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    ),
                                    size="2",
                                ),
                                spacing="2",
                            ),
                            color_scheme=rx.cond(
                                State.starting_platform | State.stopping_platform | State.status_loading,
                                "blue",
                                rx.cond(
                                    State.platform_state == "running",
                                    "green",
                                    rx.cond(
                                        State.platform_state == "deployed",
                                        "orange",
                                        "gray"
                                    )
                                )
                            ),
                            size="2",
                        ),
                        spacing="3",
                    ),

                    # Connection info
                    rx.hstack(
                        rx.cond(
                            State.is_local_connection,
                            # Local connection badge
                            rx.badge(
                                rx.hstack(
                                    rx.icon("monitor", size=12),
                                    rx.text("Local Connection", size="1", weight="medium"),
                                    spacing="1",
                                    align="center",
                                ),
                                variant="soft",
                                color_scheme="gray",
                            ),
                            # SSH connection badge with copy
                            rx.badge(
                                rx.hstack(
                                    rx.icon("terminal", size=12),
                                    rx.text("SSH:", size="1", weight="medium"),
                                    rx.text(
                                        State.working_platform.host.ansible_user + "@" +
                                        State.working_platform.host.ansible_host + ":" +
                                        State.working_platform.host.ansible_port,
                                        size="1",
                                    ),
                                    rx.icon("copy", size=12),
                                    spacing="1",
                                    align="center",
                                ),
                                variant="soft",
                                color_scheme="gray",
                                on_click=rx.call_script(
                                    "navigator.clipboard.writeText('" +
                                    "ssh -p " + State.working_platform.host.ansible_port + " " +
                                    State.working_platform.host.ansible_user + "@" +
                                    State.working_platform.host.ansible_host + "')"
                                ),
                                style={"cursor": "pointer"},
                            ),
                        ),
                        rx.badge(
                            rx.hstack(
                                rx.icon("folder", size=12),
                                rx.text("VOLTTRON_HOME:", size="1", weight="medium"),
                                rx.text(State.working_platform.host.volttron_home, size="1"),
                                rx.icon("copy", size=12),
                                spacing="1",
                                align="center",
                            ),
                            variant="soft",
                            color_scheme="gray",
                            on_click=rx.call_script(
                                "navigator.clipboard.writeText('" +
                                "export VOLTTRON_HOME=" + State.working_platform.host.volttron_home + "')"
                            ),
                            style={"cursor": "pointer"},
                        ),
                        rx.badge(
                            rx.hstack(
                                rx.icon("box", size=12),
                                rx.text("venv:", size="1", weight="medium"),
                                rx.text(State.working_platform.host.volttron_venv, size="1"),
                                rx.icon("copy", size=12),
                                spacing="1",
                                align="center",
                            ),
                            variant="soft",
                            color_scheme="gray",
                            on_click=rx.call_script(
                                "navigator.clipboard.writeText('" +
                                "source " + State.working_platform.host.volttron_venv + "/bin/activate" + "')"
                            ),
                            style={"cursor": "pointer"},
                        ),
                        spacing="2",
                        wrap="wrap",
                        padding_y="0.5rem",
                    ),

                    # Header with refresh button
                    rx.hstack(
                        rx.heading("Platform Status", size="6"),
                        rx.hstack(
                            # Start/Stop buttons
                            rx.cond(
                                State.platform_state == "running",
                                rx.button(
                                    rx.icon("square", size=18),
                                    "Stop Platform",
                                    on_click=State.handle_stop_platform,
                                    loading=State.stopping_platform,
                                    disabled=State.status_loading | State.starting_platform,
                                    size="2",
                                    variant="soft",
                                    color_scheme="red",
                                ),
                                rx.button(
                                    rx.icon("play", size=18),
                                    "Start Platform",
                                    on_click=State.handle_start_platform,
                                    loading=State.starting_platform,
                                    size="2",
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
                                size="2",
                                variant="soft",
                            ),
                            spacing="2",
                        ),
                        justify="between",
                        width="100%",
                        padding_bottom="1rem",
                    ),
                    
                    # Status overview
                    rx.card(
                        rx.vstack(
                            rx.heading("Instance Information", size="4"),
                            rx.divider(),
                            rx.grid(
                                # Platform ID
                                rx.vstack(
                                    rx.text("Instance Name", size="2", weight="bold", color="gray"),
                                    rx.text(State.platform_status.get("platform_id", "N/A"), size="3"),
                                    align="start",
                                    spacing="1",
                                ),
                                # Platform State
                                rx.vstack(
                                    rx.text("State", size="2", weight="bold", color="gray"),
                                    rx.badge(
                                        State.platform_state,
                                        color_scheme=rx.cond(
                                            State.platform_state == "running",
                                            "green",
                                            rx.cond(
                                                State.platform_state == "deployed",
                                                "blue",
                                                "gray"
                                            )
                                        ),
                                        size="2",
                                    ),
                                    align="start",
                                    spacing="1",
                                ),
                                # Host Configured
                                rx.vstack(
                                    rx.text("Host Configured", size="2", weight="bold", color="gray"),
                                    rx.cond(
                                        State.platform_status.get("host_configured", False),
                                        rx.hstack(
                                            rx.icon("check", size=16, color="green"),
                                            rx.text("Yes", size="3"),
                                            spacing="2",
                                        ),
                                        rx.hstack(
                                            rx.icon("x", size=16, color="red"),
                                            rx.text("No", size="3"),
                                            spacing="2",
                                        ),
                                    ),
                                    align="start",
                                    spacing="1",
                                ),
                                # Keys Verified
                                rx.vstack(
                                    rx.text("Keys Verified", size="2", weight="bold", color="gray"),
                                    rx.cond(
                                        State.is_local_connection,
                                        rx.text("N/A (local)", size="3", color="gray"),
                                        rx.cond(
                                            State.platform_status.get("keys_verified", False),
                                            rx.hstack(
                                                rx.icon("check", size=16, color="green"),
                                                rx.text("Yes", size="3"),
                                                spacing="2",
                                            ),
                                            rx.hstack(
                                                rx.icon("x", size=16, color="red"),
                                                rx.text("No", size="3"),
                                                spacing="2",
                                            ),
                                        ),
                                    ),
                                    align="start",
                                    spacing="1",
                                ),
                                columns="4",
                                spacing="4",
                                width="100%",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        width="100%",
                    ),
                    
                    # Agents section
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.heading("Agents", size="4"),
                                rx.button(
                                    rx.icon("plus", size=16),
                                    "Add Agent",
                                    on_click=State.open_install_agent_dialog,
                                    size="2",
                                    variant="soft",
                                ),
                                justify="between",
                                width="100%",
                            ),
                            rx.divider(),
                            rx.cond(
                                State.platform_agents_list,
                                rx.table.root(
                                    rx.table.header(
                                        rx.table.row(
                                            rx.table.column_header_cell("Agent"),
                                            rx.table.column_header_cell("Identity"),
                                            rx.table.column_header_cell("State"),
                                            rx.table.column_header_cell("Health"),
                                            rx.table.column_header_cell("Actions"),
                                        ),
                                    ),
                                    rx.table.body(
                                        rx.foreach(
                                            State.platform_agents_list,
                                            lambda agent: rx.table.row(
                                                rx.table.cell(rx.text(agent.get("name", ""), size="2")),
                                                rx.table.cell(rx.text(agent.get("identity", ""), size="2", weight="medium")),
                                                rx.table.cell(
                                                    rx.badge(
                                                        agent.get("state", "unknown"),
                                                        color_scheme=rx.cond(
                                                            agent.get("state") == "running",
                                                            "green",
                                                            "gray",
                                                        ),
                                                    ),
                                                ),
                                                rx.table.cell(rx.text(agent.get("health", ""), size="2")),
                                                rx.table.cell(
                                                    rx.hstack(
                                                        # Start button (show when stopped)
                                                        rx.cond(
                                                            agent.get("state") != "running",
                                                            rx.icon_button(
                                                                rx.icon("play", size=18),
                                                                on_click=lambda: State.handle_start_agent(agent.get("uuid")),
                                                                loading=State.starting_agent_uuid == agent.get("uuid"),
                                                                size="2",
                                                                variant="soft",
                                                                color_scheme="green",
                                                            ),
                                                        ),
                                                        # Stop button (show when running)
                                                        rx.cond(
                                                            agent.get("state") == "running",
                                                            rx.icon_button(
                                                                rx.icon("square", size=18),
                                                                on_click=lambda: State.handle_stop_agent(agent.get("uuid")),
                                                                loading=State.stopping_agent_uuid == agent.get("uuid"),
                                                                size="2",
                                                                variant="soft",
                                                                color_scheme="orange",
                                                            ),
                                                        ),
                                                        # Config button
                                                        rx.icon_button(
                                                            rx.icon("settings", size=18),
                                                            size="2",
                                                            variant="ghost",
                                                            color_scheme="gray",
                                                        ),
                                                        # Remove button
                                                        rx.icon_button(
                                                            rx.icon("trash-2", size=18),
                                                            on_click=lambda _, agent_uuid=agent.get("uuid"), agent_name=agent.get("name"): State.open_remove_agent_dialog(agent_uuid, agent_name),
                                                            loading=State.removing_agent_uuid == agent.get("uuid"),
                                                            size="2",
                                                            variant="ghost",
                                                            color_scheme="red",
                                                            disabled=State.removing_agent_uuid != "",
                                                        ),
                                                        spacing="2",
                                                        align="center",
                                                    ),
                                                    justify="end",
                                                ),
                                            )
                                        ),
                                    ),
                                    width="100%",
                                    size="2",
                                ),
                                rx.text("No agents installed. Click 'Add Agent' to install one.", size="3", color="gray"),
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        width="100%",
                    ),
                    
                    # Last check timestamp
                    rx.cond(
                        State.last_status_check != "",
                        rx.text(
                            f"Last updated: {State.last_status_check}",
                            size="1",
                            color="gray",
                        ),
                    ),
                    
                    # Error message
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
                    
                    # Periodic connection check (every 15 seconds)
                    rx.moment(
                        interval=15000,
                        on_change=State.check_connection,
                        display="none",
                    ),
                    
                    spacing="4",
                    width="100%",
                ),
                padding="1rem",
            ),
            # Show message for non-deployed platforms
            rx.container(
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
                padding="1rem",
            ),
        ),
    )
