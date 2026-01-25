import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.tiles import config_tile
from ..components.buttons import icon_button_wrapper
from ..components.header.header import header
from ..components.buttons.tile_icon import tile_icon
from ..navigation.state import NavigationState
from ..components.form_components import form_entry
from typing import Literal
from ..thin_endpoint_wrappers import *
from ..state import PlatformPageState as State
from ..models import Instance

parts = Literal["connection", "instance_configuration"]

def deployment_progress_dialog() -> rx.Component:
    """Dialog showing deployment progress with task name and logs"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Deploying Platform"),
                rx.dialog.description(
                    rx.text(State.current_task, size="3", weight="bold")
                ),
                rx.progress(value=State.deployment_progress, max=100, width="100%"),
                rx.text(
                    rx.cond(
                        State.deployment_progress > 0,
                        f"{State.deployment_progress}% complete",
                        "Starting...",
                    ),
                    size="1",
                    color="gray",
                ),
                rx.cond(
                    State.show_pyenv_prompt,
                    rx.callout(
                        rx.vstack(
                            rx.text(
                                rx.cond(
                                    State.pyenv_error != "",
                                    State.pyenv_error,
                                    "Python 3.10 is required but not found.",
                                ),
                                weight="bold",
                            ),
                            rx.text(
                                "After installing Python 3.10, add the path to the platform's Advanced Settings (Custom Python Path).",
                                size="1",
                            ),
                            spacing="1",
                            align="start",
                        ),
                        icon="triangle_alert",
                        color="yellow",
                        size="2",
                    ),
                    rx.fragment(),
                ),
                rx.box(
                    rx.vstack(
                        rx.foreach(
                            State.deployment_steps,
                            lambda step: rx.hstack(
                                rx.cond(
                                    step["status"] == "running",
                                    rx.spinner(size="1"),
                                    rx.cond(
                                        step["status"] == "success",
                                        rx.icon("check", size=16, color="green"),
                                        rx.icon("x", size=16, color="red"),
                                    ),
                                ),
                                rx.text(step["name"], size="2"),
                                spacing="2",
                                align="center",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    width="100%",
                    padding="0.5rem",
                    border="1px solid var(--gray-4)",
                    border_radius="8px",
                    background_color="var(--gray-1)",
                ),
                # Log output area
                rx.box(
                    rx.vstack(
                        rx.foreach(
                            State.deployment_logs,
                            lambda log: rx.text(log, size="1", font_family="monospace")
                        ),
                        width="100%",
                        spacing="1",
                    ),
                    width="100%",
                    height=rx.cond(State.show_pyenv_prompt, "220px", "300px"),
                    overflow_y="auto",
                    padding="1rem",
                    border="1px solid var(--gray-6)",
                    border_radius="8px",
                    background_color="var(--gray-2)",
                ),
                # Progress indicator
                rx.cond(
                    State.is_deploying,
                    rx.hstack(
                        rx.spinner(size="3"),
                        rx.text("Deploying...", size="2"),
                        spacing="3",
                        align="center",
                    ),
                    rx.cond(
                        State.deployment_status == "success",
                        rx.hstack(
                            rx.icon("check", size=24, color="green"),
                            rx.text("Deployment completed", size="2", color="green"),
                            spacing="3",
                            align="center",
                        ),
                        rx.hstack(
                            rx.icon("x", size=24, color="red"),
                            rx.text("Deployment failed", size="2", color="red"),
                            spacing="3",
                            align="center",
                        ),
                    ),
                ),
                # Action buttons
                rx.hstack(
                    rx.cond(
                        State.show_pyenv_prompt,
                        rx.button(
                            "Install Python 3.10 with pyenv",
                            on_click=State.handle_install_pyenv,
                            disabled=State.pyenv_installing,
                            loading=State.pyenv_installing,
                        ),
                        rx.fragment(),
                    ),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            on_click=State.close_deployment_dialog,
                            disabled=State.is_deploying,
                        )
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
        open=State.show_deployment_dialog,
    )


def pyenv_install_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Install Python 3.10 via pyenv"),
                rx.dialog.description(
                    "Install Python 3.10 on the remote host using pyenv and create the VOLTTRON venv.",
                    size="1",
                ),
                rx.text(
                    "Python 3.10 is required but not found on the remote host. "
                    "Would you like to install it using pyenv?",
                    size="2",
                    color="gray",
                ),
                rx.cond(
                    State.pyenv_error != "",
                    rx.callout(
                        State.pyenv_error,
                        icon="triangle_alert",
                        color="red",
                        size="1",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    State.pyenv_installing,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("Installing Python 3.10 via pyenv... This may take several minutes.", size="2"),
                        spacing="2",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.button(
                        "Install with pyenv",
                        on_click=State.handle_install_pyenv,
                        disabled=State.pyenv_installing,
                        loading=State.pyenv_installing,
                    ),
                    rx.button(
                        "Cancel",
                        variant="soft",
                        on_click=State.close_pyenv_dialog,
                        disabled=State.pyenv_installing,
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            max_width="600px",
        ),
        open=State.show_pyenv_dialog,
    )

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

@rx.page(route="/platform/[uid]", on_load=State.hydrate_state)
def platform_page() -> rx.Component:

    # State.working_platform: Instance = State.platforms[State.current_uid]

    return rx.cond(
        State.is_hydrated, 
        rx.fragment(
            app_layout(
                header(
                    rx.hstack(
                        icon_button_wrapper.icon_button_wrapper(
                            tool_tip_content="Go back to overview",
                            icon_key="arrow-left",
                            on_click=NavigationState.route_to_index
                        ),
                        rx.text(f"""{
                                rx.cond(
                                    State.working_platform.new_instance,
                                    'New Platform',
                                    f'Platform: {State.platform_title}'
                                )
                            }""",
                            trim="both",
                            size="6"
                        ),
                        spacing="6",
                        align="center",
                    ),
                    rx.hstack(
                        rx.cond(
                            State.working_platform.new_instance==False,
                            icon_button_wrapper.icon_button_wrapper(
                                tool_tip_content="Copy Platform",
                                icon_key="copy",
                                on_click=State.copy_platform(State.current_uid)
                            )
                        ),
                        # Delete button opens dialog
                        icon_button_wrapper.icon_button_wrapper(
                            tool_tip_content="Delete platform",
                            icon_key="trash-2",
                            on_click=State.open_delete_dialog,
                        ),
                        # Delete Platform Dialog
                        rx.dialog.root(
                            rx.dialog.content(
                                rx.cond(
                                    ~State.delete_confirmed,
                                    # Step 1: Delete options
                                    rx.vstack(
                                        rx.dialog.title("Delete Platform"),
                                        rx.dialog.description(
                                            "Choose what to delete:",
                                            size="2",
                                        ),
                                        rx.vstack(
                                            rx.hstack(
                                                rx.checkbox(
                                                    checked=State.delete_remote_files,
                                                    on_change=State.toggle_delete_remote_files,
                                                ),
                                                rx.vstack(
                                                    rx.text("Also delete VOLTTRON files on remote system", weight="medium"),
                                                    rx.text(
                                                        "This will stop VOLTTRON, delete ~/.volttron and the virtual environment",
                                                        size="1",
                                                        color="gray",
                                                    ),
                                                    align="start",
                                                    spacing="0",
                                                ),
                                                align="start",
                                                spacing="2",
                                            ),
                                            padding="1rem",
                                            background="var(--gray-2)",
                                            border_radius="var(--radius-2)",
                                            width="100%",
                                        ),
                                        rx.flex(
                                            rx.button(
                                                "Cancel",
                                                variant="soft",
                                                color_scheme="gray",
                                                on_click=State.close_delete_dialog,
                                            ),
                                            rx.button(
                                                "Continue",
                                                color_scheme="red",
                                                on_click=State.confirm_delete,
                                            ),
                                            spacing="3",
                                            margin_top="16px",
                                            justify="end",
                                        ),
                                        spacing="3",
                                        width="100%",
                                    ),
                                    # Step 2: Confirmation
                                    rx.vstack(
                                        rx.dialog.title(
                                            rx.hstack(
                                                rx.icon("alert-triangle", color="red", size=24),
                                                "Confirm Deletion",
                                                spacing="2",
                                            )
                                        ),
                                        rx.callout(
                                            rx.cond(
                                                State.delete_remote_files,
                                                "This will permanently delete the platform configuration AND all VOLTTRON files on the remote system. This cannot be undone!",
                                                "This will permanently delete the platform configuration. This cannot be undone!",
                                            ),
                                            icon="alert-triangle",
                                            color="red",
                                        ),
                                        rx.cond(
                                            State.deleting_platform,
                                            rx.hstack(
                                                rx.spinner(size="2"),
                                                rx.text("Deleting platform..."),
                                                spacing="2",
                                                padding="1rem",
                                            ),
                                            rx.flex(
                                                rx.button(
                                                    "Back",
                                                    variant="soft",
                                                    color_scheme="gray",
                                                    on_click=State.back_to_delete_options,
                                                ),
                                                rx.button(
                                                    rx.cond(
                                                        State.delete_remote_files,
                                                        "Delete Platform & Remote Files",
                                                        "Delete Platform",
                                                    ),
                                                    color_scheme="red",
                                                    on_click=State.handle_delete_platform,
                                                ),
                                                spacing="3",
                                                margin_top="16px",
                                                justify="end",
                                            ),
                                        ),
                                        spacing="3",
                                        width="100%",
                                    ),
                                ),
                                max_width="450px",
                            ),
                            open=State.show_delete_dialog,
                        ),
                    ),
                    justify="between"
                ),
                platform_tabs()
            ),
            deployment_progress_dialog(),
            pyenv_install_dialog(),
            install_agent_dialog(),
        ),
        # Skeleton Stuff
        rx.vstack(
            # Header
            rx.hstack(
                rx.hstack(
                    rx.skeleton(
                        rx.box(),
                        height="3rem",
                        width="5rem",
                        radius="5rem",
                        loading=True,
                    ),
                    rx.skeleton(
                        rx.box(),
                        height="3rem",
                        width="12rem",
                        radius="5rem",
                        loading=True,
                    ),
                    spacing="4",
                    align="center",
                ),
                rx.skeleton(
                    rx.box(),
                    height="3rem",
                    width="5rem",
                    radius="5rem",
                    loading=True,
                ),
                spacing="4",
                align="center",
                justify="between",
                width="100%",
            ),
            # Tabs divider
            rx.skeleton(
                rx.box(),
                width="100%",
                height="15px",
                loading=True,
            ),
            spacing="6",
            padding="1rem"
        )
    )

# TODO: clean up these components to make it more readable and separated. 
# These components all work if they have the right setup which follows:
# def function() -> rx.Component:
#   State.working_platform: Instance = State.platforms[State.current_uid]
#   return rx.cond(State.is_hydrated,
#             rest of component...
#             )


def platform_tabs() -> rx.Component:
    # State.working_platform: Instance = State.platforms[State.current_uid]
    return rx.cond(
        State.is_hydrated,
        rx.box(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        "Status", value="status", disabled=rx.cond(
                            State.working_platform.platform.in_file,
                            False,
                            True
                        )
                    ),
                    rx.tabs.trigger("Configuration", value="configuration"),
                    rx.tabs.trigger(
                        "Logs", value="logs", disabled=rx.cond(
                            State.working_platform.platform.in_file,
                            False,
                            True
                        )
                    ),
                ),
                rx.tabs.content(
                    rx.box(
                        data_tab_content(),
                        on_mount=[State.refresh_platform_status, State.check_connection],
                    ),
                    value="status"
                ),
                rx.tabs.content(
                    rx.box(
                        configuration_tab_content(),
                        padding="1rem"
                    ),
                    value="configuration"
                ),
                rx.tabs.content(
                    rx.box(
                        logs_tab_content(),
                        padding="1rem"
                    ),
                    value="logs"
                ),
                default_value=rx.cond(
                    State.working_platform.platform.in_file,
                    "status",
                    "configuration"
                )
            )
        )
    )

# Logs tab content:
def logs_tab_content() -> rx.Component:
    """Tab content for viewing VOLTTRON logs"""
    return rx.vstack(
        rx.hstack(
            rx.heading("VOLTTRON Logs", size="5"),
            rx.hstack(
                rx.button(
                    rx.icon("minus", size=18),
                    "Smaller",
                    on_click=State.decrease_log_font_size,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("plus", size=18),
                    "Larger",
                    on_click=State.increase_log_font_size,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("wrap-text", size=18),
                    "Wrap",
                    on_click=State.toggle_log_wrap,
                    size="2",
                    variant=rx.cond(State.log_wrap, "solid", "soft"),
                ),
                rx.cond(
                    State.tailing,
                    rx.button(
                        rx.icon("square", size=18),
                        "Stop Tail",
                        on_click=State.stop_tailing,
                        size="2",
                        variant="solid",
                        color_scheme="red",
                    ),
                    rx.button(
                        rx.icon("play", size=18),
                        "Live Tail",
                        on_click=State.start_tailing,
                        size="2",
                        variant="soft",
                        color_scheme="green",
                    ),
                ),
                rx.button(
                    rx.icon("refresh-cw", size=18),
                    "Refresh Logs",
                    on_click=State.fetch_platform_logs(100),
                    loading=State.logs_loading,
                    disabled=State.tailing,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("trash-2", size=18),
                    "Delete Log",
                    on_click=State.delete_platform_logs,
                    loading=State.logs_loading,
                    disabled=State.tailing,
                    size="2",
                    variant="soft",
                    color_scheme="red",
                ),
                spacing="2",
            ),
            justify="between",
            width="100%",
            padding_bottom="1rem",
        ),
        rx.card(
            rx.scroll_area(
                rx.el.pre(
                    rx.foreach(
                        State.parsed_log_lines,
                        lambda log_line: rx.el.div(
                            log_line["text"],
                            style={
                                "color": rx.match(
                                    log_line["level"],
                                    ("debug", "var(--gray-9)"),
                                    ("info", "var(--blue-11)"),
                                    ("warning", "var(--orange-11)"),
                                    ("error", "var(--red-11)"),
                                    ("critical", "var(--red-12)"),
                                    "var(--gray-12)",
                                ),
                                "fontWeight": rx.cond(
                                    log_line["level"] == "critical",
                                    "bold",
                                    "normal",
                                ),
                            },
                        ),
                    ),
                    style={
                        "fontSize": State.log_font_size.to(str) + "px",
                        "whiteSpace": rx.cond(State.log_wrap, "pre-wrap", "pre"),
                        "wordBreak": rx.cond(State.log_wrap, "break-word", "normal"),
                        "overflowWrap": rx.cond(State.log_wrap, "break-word", "normal"),
                        "fontFamily": "monospace",
                        "margin": "0",
                        "padding": "1em",
                        "backgroundColor": "var(--gray-2)",
                        "borderRadius": "var(--radius-2)",
                    },
                ),
                type="auto",
                scrollbars="both",
                style={"height": "calc(100vh - 250px)", "width": "100%"},
            ),
            width="100%",
        ),
        spacing="3",
        width="100%",
    )

# Config tab and it's components:
def configuration_tab_content() -> rx.Component:
    # State.working_platform: Instance = State.platforms[State.current_uid]
    
    return rx.cond(State.is_hydrated, 
            rx.box(
                rx.accordion.root(
                    rx.accordion.item(
                        header="Connection",
                        value="connection",
                        # content=rx.box(
                        #     connection_accordion_content(State.working_platform)
                        # ),
                        content=rx.box(
                            rx.box(
                                rx.hstack(
                                    rx.text("Install Locally?", size="2", color="gray", weight="medium"),
                                    rx.button(
                                        "Use Local Connection",
                                        variant="soft",
                                        size="2",
                                        on_click=State.use_local_details,
                                    ),
                                    align="center",
                                    spacing="2",
                                    margin_bottom="1rem",
                                ),
                                form_entry.form_entry(
                                    "Host",
                                    rx.input(
                                        value= State.working_platform.host.ansible_host,
                                        on_change=lambda v: State.update_detail("id", v),
                                        size="3",
                                        required=True,
                                        on_blur=State.determine_host_reachability(State.working_platform),
                                        color_scheme = rx.cond(
                                            State.is_host_resolvable,
                                            "gray",
                                            "red"
                                        )
                                    ),
                                    required_entry=True,
                                    upload=rx.cond(
                                        State.host_pinging,
                                        rx.spinner(),
                                        # rx.tooltip(
                                        #     "Resolving host...",    
                                        #     rx.spinner()
                                        # ),
                                        rx.cond(
                                            State.is_host_resolvable,
                                            tile_icon(
                                                "check"
                                            ),
                                            tile_icon(
                                                "triangle-alert"
                                            )
                                        )
                                    ),
                                    below_component=rx.cond(
                                        State.is_host_resolvable == False,
                                        rx.text(
                                            "Host must be a valid domain or ip address", 
                                            color_scheme="red"
                                        )
                                    ),
                                ),
                                form_entry.form_entry(
                                    "Username",
                                    rx.input(
                                        value= State.working_platform.host.ansible_user,
                                        on_change=lambda v: State.update_detail("ansible_user", v),
                                        size="3",
                                        required=True,
                                    ),
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="SSH username on the remote host. This user must have SUDO permissions to install and configure VOLTTRON."
                                    ),
                                    required_entry=True,
                                ),
                                form_entry.form_entry(
                                    "Port SSH",
                                    rx.input(
                                        value= State.working_platform.host.ansible_port,
                                        on_change=lambda v: State.update_detail("ansible_port", v),
                                        size="3",
                                        required=True,
                                    ),
                                    required_entry=True,
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="SSH port on the remote host (default: 22)"
                                    ),
                                    below_component=rx.cond(
                                        State.connection_ansible_port_validity == False,
                                        rx.text(
                                            "Port SSH must be a valid port number",
                                            color_scheme="red"
                                        )
                                    ),
                                ),
                                rx.box(
                                    rx.hstack(
                                        rx.text("Toggle Advanced"),
                                        rx.cond(
                                            State.working_platform.advanced_expanded,
                                            rx.icon("chevron-up"),
                                            rx.icon("chevron-down")
                                        )
                                    ),
                                    class_name="toggle_advanced_button",
                                    on_click=State.toggle_advanced(State.current_uid)
                                ),
                                rx.cond(
                                    State.working_platform.advanced_expanded,
                                    rx.fragment(
                                        form_entry.form_entry(
                                            "HTTP Proxy",
                                            rx.input(
                                                value= State.working_platform.host.http_proxy,
                                                on_change=lambda v: State.update_detail("http_proxy", v),
                                                size="3",
                                            ),
                                            upload=tile_icon(
                                                "badge-info",
                                                tooltip="Optional HTTP proxy for connecting through a firewall (e.g., http://proxy:8080)"
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "HTTPS Proxy",
                                            rx.input(
                                                value= State.working_platform.host.https_proxy,
                                                on_change=lambda v: State.update_detail("https_proxy", v),
                                                size="3",
                                            ),
                                            upload=tile_icon(
                                                "badge-info",
                                                tooltip="Optional HTTPS proxy for connecting through a firewall (e.g., https://proxy:8080)"
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "VOLTTRON Home",
                                            rx.input(
                                                value= State.working_platform.host.volttron_home,
                                                on_change=lambda v: State.update_detail("volttron_home", v),
                                                size="3",
                                            ),
                                            upload=tile_icon(
                                                "badge-info",
                                                tooltip="Directory where VOLTTRON stores its data and configuration (default: ~/.volttron)"
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "VOLTTRON venv",
                                            rx.input(
                                                value= State.working_platform.host.volttron_venv,
                                                on_change=lambda v: State.update_detail("volttron_venv", v),
                                                size="3",
                                            ),
                                            upload=tile_icon(
                                                "badge-info",
                                                tooltip="Path to the Python virtual environment used to run VOLTTRON (default: ~/volttron.venv)"
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "VOLTTRON Source",
                                            rx.input(
                                                value= State.working_platform.host.volttron_source,
                                                on_change=lambda v: State.update_detail("volttron_source", v),
                                                size="3",
                                            ),
                                            upload=tile_icon(
                                                "badge-info",
                                                tooltip="Path to VOLTTRON source code for monolithic installations (default: ~/volttron). Only used for monolithic VOLTTRON."
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "Ignore Host Keys",
                                            rx.checkbox(
                                                checked=State.working_platform.host.ignore_host_keys,
                                                on_change=lambda v: State.update_detail("ignore_host_keys", v),
                                                size="3",
                                            ),
                                            upload=tile_icon(
                                                "badge-info",
                                                tooltip="Skip SSH host key verification (StrictHostKeyChecking=no). Use if the remote host is not in your known_hosts file. Less secure but useful for initial setup."
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "Custom Python Path",
                                            rx.input(
                                                value=State.working_platform.platform.config.custom_python_path,
                                                on_change=lambda v: State.update_platform_config_detail("custom_python_path", v),
                                                placeholder="e.g. ~/.pyenv/versions/3.10.14/bin/python3",
                                                size="3",
                                            ),
                                            upload=tile_icon(
                                                "badge-info",
                                                tooltip="Optional: Specify a custom Python 3.10 executable. Useful when system Python is not 3.10. Leave empty for auto-detection."
                                            )
                                        ),
                                    )
                                ),
                                class_name="platform_content_view"
                            ),
                            class_name="platform_content_container"
                        )
                    ),
                    rx.accordion.item(
                        header="Instance Configuration",
                        value="instance_configuration",
                        # content=rx.box(
                        #     instance_configuration_accordion_content(State.working_platform)
                        # ),
                        content=rx.box(
                            rx.box(
                                form_entry.form_entry( # validate
                                    "Instance Name",
                                    rx.vstack(
                                        rx.input(
                                            size="3",
                                            value=State.working_platform.platform.config.instance_name,
                                            on_change=lambda v: State.update_platform_config_detail("instance_name", v),
                                            required=True,
                                        ),
                                        align="center"
                                    ),
                                    below_component=rx.fragment(
                                        rx.cond(
                                            State.platform_instance_name_validity == False,
                                            rx.text(
                                                "Instance Name must contain only letters, numbers, hyphens, and underscores", 
                                                color_scheme="red"
                                            )
                                        ),
                                        rx.cond(
                                            State.platform_instance_name_not_in_use == False,
                                            rx.text(
                                                "Instance Name already in use", 
                                                color_scheme="red"
                                            )
                                        )
                                    ),
                                    required_entry=True,
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="Instance Name must contain only letters, numbers, hyphens, and underscores"
                                    )
                                ),
                                form_entry.form_entry(
                                    "VOLTTRON Type",
                                    rx.vstack(
                                        rx.hstack(
                                            rx.button(
                                                "Modular",
                                                on_click=lambda: State.update_platform_config_detail("volttron_type", "modular"),
                                                variant=rx.cond(
                                                    State.working_platform.platform.config.volttron_type == "modular",
                                                    "solid",
                                                    "soft"
                                                ),
                                                color_scheme=rx.cond(
                                                    State.working_platform.platform.config.volttron_type == "modular",
                                                    "blue",
                                                    "gray"
                                                ),
                                                size="2",
                                                style={"flex": "1"},
                                            ),
                                            rx.button(
                                                "Monolithic",
                                                on_click=lambda: State.update_platform_config_detail("volttron_type", "monolithic"),
                                                variant=rx.cond(
                                                    State.working_platform.platform.config.volttron_type == "monolithic",
                                                    "solid",
                                                    "soft"
                                                ),
                                                color_scheme=rx.cond(
                                                    State.working_platform.platform.config.volttron_type == "monolithic",
                                                    "blue",
                                                    "gray"
                                                ),
                                                size="2",
                                                style={"flex": "1"},
                                            ),
                                            spacing="2",
                                            width="100%",
                                        ),
                                        rx.text(
                                            rx.cond(
                                                State.working_platform.platform.config.volttron_type == "modular",
                                                "Modular: Agents are pip packages installed independently. Modern, flexible, easier to maintain.",
                                                "Monolithic: All-in-one VOLTTRON installation with agents included. Traditional approach."
                                            ),
                                            size="1",
                                            color="gray",
                                        ),
                                        spacing="2",
                                        align="start",
                                        width="100%",
                                    ),
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="Modular uses pip packages for agents (recommended). Monolithic includes all agents in one installation."
                                    )
                                ),
                                rx.cond(
                                    State.working_platform.platform.config.volttron_type == "modular",
                                    form_entry.form_entry(
                                        "VOLTTRON Version",
                                        rx.input(
                                            value=State.working_platform.platform.config.volttron_version,
                                            on_change=lambda v: State.update_platform_config_detail("volttron_version", v),
                                            placeholder="e.g. 2.0.0rc20 or user/volttron-core@branch",
                                            size="3",
                                        ),
                                        upload=tile_icon(
                                            "badge-info",
                                            tooltip="Leave empty for latest PyPI. Or specify: version (2.0.0rc20), GitHub shorthand (user/repo@branch), or full git URL (git+https://...)."
                                        )
                                    ),
                                ),
                                form_entry.form_entry( # validate
                                    "Vip Address",
                                    rx.vstack(
                                        rx.input(
                                            size="3",
                                            value=State.working_platform.platform.config.vip_address,
                                            on_change=lambda v: State.update_platform_config_detail("vip_address", v),
                                            required=True,
                                        ),  
                                        align="center"
                                    ),
                                    below_component=rx.cond(
                                        State.platform_vip_address_validity == False,
                                        rx.text(
                                            "Vip Address must be in the format tcp://<ip>:<port>", 
                                            color_scheme="red"
                                        )
                                    ),
                                    required_entry=True,
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="VIP (VOLTTRON Interconnect Protocol) address for agent communication. Format: tcp://<ip>:<port>"
                                    )
                                ),
                                form_entry.form_entry(
                                    "Member of Federation",
                                    rx.vstack(
                                        rx.checkbox(
                                            size="3",
                                            on_click=State.toggle_federation
                                        ),
                                        justify="center",
                                        align="center",
                                        width="100%"
                                    ),
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="Enable to connect this platform to a VOLTTRON federation for multi-platform communication and data sharing."
                                    )
                                ),
                                form_entry.form_entry(
                                    "Web",
                                    rx.vstack(
                                        rx.checkbox(
                                            size="3",
                                            checked=State.working_platform.web_checked,
                                            on_change=State.toggle_web
                                        ),
                                        justify="center",
                                        align="center",
                                        width="100%"
                                    ),
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="Enable the VOLTTRON web interface for browser-based platform management and monitoring."
                                    )
                                ),
                                rx.cond(
                                    State.working_platform.web_checked,
                                    rx.fragment(
                                        form_entry.form_entry(
                                            "Web Bind Address",
                                            rx.input(
                                                size="3",
                                                value=State.working_platform.web_bind_address,
                                                on_change=lambda v: State.update_platform_config_detail("web_bind_address", v),
                                                required=True,
                                            ),
                                            upload=tile_icon(
                                                "badge-info",
                                                tooltip="Address and port for the web interface (e.g., https://0.0.0.0:8443). Use 0.0.0.0 to listen on all interfaces."
                                            )
                                        )
                                    )
                                ),
                                rx.box(
                                    rx.hstack(
                                        rx.text("Agent Configuration"),
                                        rx.cond(
                                            State.working_platform.agent_configuration_expanded,
                                            rx.icon("chevron-up"),
                                            rx.icon("chevron-down")
                                        )
                                    ),
                                    class_name="toggle_advanced_button",
                                    on_click=State.toggle_agent_config_details
                                ),
                                rx.box(
                                    rx.cond(
                                        State.working_platform.agent_configuration_expanded,
                                        rx.el.div(
                                            rx.box(
                                                rx.box(
                                                    rx.heading("Listed Agents", as_="h3"),
                                                    rx.foreach(
                                                        State.list_of_agents,
                                                        lambda agent, index: config_tile.config_tile(
                                                            agent.identity,
                                                            right_component=tile_icon(
                                                                "plus",
                                                                on_click=State.handle_adding_agent(agent, State.current_uid)
                                                            ),
                                                        ),
                                                    ),
                                                    class_name="agent_config_view_content"
                                                ),
                                                class_name="agent_config_views"
                                            ),
                                            rx.box(
                                                rx.box(
                                                    rx.heading("Added Agents", as_="h3"),
                                                    rx.foreach(
                                                        State.working_platform.platform.agents,
                                                        lambda identity_agent_pair: config_tile.config_tile(
                                                            identity_agent_pair[1].identity,
                                                            left_component=tile_icon(
                                                                "trash-2",
                                                                on_click=State.handle_removing_agent(identity_agent_pair[0])
                                                            ),
                                                            right_component=tile_icon(
                                                                "settings",
                                                                on_click=NavigationState.route_to_agent_config(
                                                                    State.current_uid,
                                                                    identity_agent_pair[1].routing_id,
                                                                    identity_agent_pair[1]
                                                                )
                                                            ),
                                                            # This works but i dont want to implement it just yet, i want more info on how
                                                            # this should ideally work
                                                            # class_name=rx.cond(
                                                            #     State.new_agents_list.contains(identity_agent_pair[1].routing_id),
                                                            #     "agent_config_tile new",
                                                            #     "agent_config_tile"
                                                            # ),
                                                            # tooltip=rx.cond(
                                                            #     State.new_agents_list.contains(identity_agent_pair[1].routing_id),
                                                            #     "This agent is loaded with default configs",
                                                            #     ""
                                                            # )
                                                        )
                                                    ),
                                                    class_name="agent_config_view_content"
                                                ),
                                                class_name="agent_config_views"
                                            ),
                                            class_name="agent_config_container"
                                        ),
                                    )
                                ),
                                class_name="platform_content_view"
                            ),
                            class_name="platform_content_container"
                        )
                    ),
                    collapsible=True,
                    default_value=["connection"],
                    type="multiple",
                    variant="outline"
                ),
                rx.box(
                    rx.button(
                        "Save", 
                        size="4", 
                        variant="surface",
                        color_scheme="green",
                        on_click=State.handle_save,
                        disabled=rx.cond(
                            (State.instance_savable)
                            & (State.instance_uncaught),
                            # (State.working_platform.uncaught),
                            False,
                            True
                        )
                    ),
                    rx.dialog.root(
                        rx.dialog.trigger(
                            rx.button(
                                rx.cond(
                                    State.platform_deployed,
                                    "Re-Deploy",
                                    "Deploy"
                                ), 
                                size="4", 
                                variant="surface", 
                                color_scheme="blue",
                                disabled=rx.cond(
                                    (State.instance_uncaught == False)
                                    & (State.instance_deployable==True),
                                    False,
                                    True
                                )
                            ),
                        ),
                        rx.dialog.content(
                            rx.dialog.title("Password Required"),
                            rx.dialog.description("To deploy, please provide your ssh password"),
                            rx.vstack(
                                rx.vstack(
                                    form_entry.form_entry(
                                        "Password",
                                        rx.input(
                                            type="password",
                                            on_change=State.update_password_field,
                                            value=State.password_field
                                        ),
                                        required_entry=True
                                    ),
                                    align="center",
                                    justify="center"
                                ),
                                rx.hstack(
                                    rx.dialog.close(
                                        rx.button(
                                            "Cancel",
                                            variant="soft",
                                            color_scheme="gray",
                                        )
                                    ),
                                    rx.dialog.close(
                                        rx.button(
                                            "Submit",
                                            on_click=State.handle_deploy,
                                            disabled=rx.cond(
                                                State.password_field=="",
                                                True,
                                                False
                                            )
                                        )
                                    ),
                                    spacing="3",
                                    justify="end",
                                ),
                                width="100%",
                                padding_top="1rem",
                                spacing="6"
                            )
                        )
                    ),
                    rx.button(
                            "Cancel", 
                            size="4", 
                            variant="surface", 
                            color_scheme="red",
                            on_click=State.handle_cancel,
                            disabled=rx.cond(
                                State.instance_uncaught == False,
                                # State.working_platform.uncaught == False,
                                True,
                                False
                            )
                        ),
                    class_name="platform_view_button_row"
                    ),
            class_name="platform_view_container"
            )
        )

# Data tab and it's components
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
                        # SSH Connection Status Badge
                        rx.tooltip(
                            rx.badge(
                                rx.hstack(
                                    rx.cond(
                                        State.connection_status == "connected",
                                        rx.icon("wifi", size=14),
                                        rx.cond(
                                            State.connection_status == "checking",
                                            rx.spinner(size="1"),
                                            rx.icon("wifi-off", size=14),
                                        ),
                                    ),
                                    rx.text(
                                        rx.cond(
                                            State.connection_status == "connected",
                                            "SSH Connected",
                                            rx.cond(
                                                State.connection_status == "checking",
                                                "Checking SSH...",
                                                rx.cond(
                                                    State.connection_status == "disconnected",
                                                    "SSH Disconnected",
                                                    "SSH Unknown"
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

                    # Remote connection info
                    rx.hstack(
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
                                "ssh -p " + State.working_platform.host.ansible_port + " " +
                                State.working_platform.host.ansible_user + "@" +
                                State.working_platform.host.ansible_host + " " +
                                "\"export VOLTTRON_HOME=" + State.working_platform.host.volttron_home + " && bash\"" + "')"
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
                                "ssh -p " + State.working_platform.host.ansible_port + " " +
                                State.working_platform.host.ansible_user + "@" +
                                State.working_platform.host.ansible_host + " " +
                                "\"source " + State.working_platform.host.volttron_venv + "/bin/activate && bash\"" + "')"
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
                                rx.vstack(
                                    rx.foreach(
                                        State.platform_agents_list,
                                        lambda agent: rx.hstack(
                                            rx.icon("package", size=16, color="var(--blue-9)"),
                                            rx.text(agent["id"], size="3"),
                                            spacing="2",
                                            padding="0.5rem",
                                            border_radius="8px",
                                            _hover={"background_color": "var(--gray-3)"},
                                        )
                                    ),
                                    width="100%",
                                    spacing="2",
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
                                rx.icon("alert-triangle", size=16),
                                rx.text(State.status_error),
                                spacing="2",
                            ),
                            color_scheme="red",
                            width="100%",
                        ),
                    ),
                    
                    # Periodic connection check (every 5 seconds)
                    rx.moment(
                        interval=5000,
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


# General components
def agent_config_tile(text, left_component: rx.Component = False, right_component: rx.Component = False)->rx.Component:
    return rx.hstack(
        rx.cond(
            left_component,
            rx.flex(
                left_component,
                align="center",
                justify="center",
            )
        ),
        rx.flex(
            rx.text(text),
            class_name=f"agent_config_tile",
        ),
        rx.cond(
            right_component,
            rx.flex(        
                right_component,
                align="center",
                justify="center"
            )
        ),  
        spacing="2",
        align="center",
    )
