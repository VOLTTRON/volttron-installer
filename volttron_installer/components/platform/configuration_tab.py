import reflex as rx
from ...state import PlatformPageState as State
from ...components.form_components import form_entry as _fe
from ...components.buttons.tile_icon import tile_icon
from ...components.tiles import config_tile
from ...navigation.state import NavigationState


# ─── helpers ────────────────────────────────────────────────────────────────

def _section(title: str, icon: str, *children) -> rx.Component:
    """Titled card section."""
    return rx.box(
        rx.hstack(
            rx.icon(icon, size=16, color="var(--accent-9)"),
            rx.text(title, size="3", weight="bold", color="var(--gray-12)"),
            spacing="2",
            align="center",
            padding_bottom="0.75rem",
            border_bottom="1px solid var(--gray-4)",
            width="100%",
            margin_bottom="1.25rem",
        ),
        *children,
        background="var(--gray-1)",
        border="1px solid var(--gray-4)",
        border_radius="10px",
        padding="1.5rem",
        width="100%",
    )


def _field(label: str, input_component: rx.Component,
           tooltip: str | None = None,
           required: bool = False,
           error: rx.Component | None = None) -> rx.Component:
    """Clean horizontal label + input row."""
    label_el = rx.hstack(
        rx.text(
            label,
            rx.cond(required, rx.text.span(" *", color="var(--red-9)"), rx.fragment()),
            size="2",
            weight="medium",
            color="var(--gray-11)",
        ),
        rx.cond(
            tooltip is not None,
            rx.tooltip(
                rx.icon("info", size=13, color="var(--gray-8)"),
                content=tooltip,
            ),
            rx.fragment(),
        ) if tooltip else rx.fragment(),
        spacing="1",
        align="center",
        width="180px",
        flex_shrink="0",
    )
    return rx.vstack(
        rx.hstack(
            label_el,
            rx.box(input_component, flex="1"),
            spacing="3",
            align="start",
            width="100%",
        ),
        rx.cond(error is not None, error, rx.fragment()) if error else rx.fragment(),
        spacing="1",
        width="100%",
        align="start",
    )


def _divider() -> rx.Component:
    return rx.divider(margin_y="1rem")


# ─── Connection section ──────────────────────────────────────────────────────

def _connection_section() -> rx.Component:
    is_local = State.working_platform.host.ansible_connection == "local"
    return _section(
        "Connection", "network",
        # Local toggle
        rx.hstack(
            rx.text("Install Locally?", size="2", color="var(--gray-10)"),
            rx.button(
                "Use Local Connection",
                variant=rx.cond(is_local, "solid", "soft"),
                color_scheme=rx.cond(is_local, "blue", "gray"),
                size="2",
                on_click=State.use_local_details,
            ),
            spacing="3",
            align="center",
            margin_bottom="1rem",
        ),
        rx.cond(
            is_local,
            rx.callout(
                rx.text("Local connection mode: No SSH or passwords needed"),
                icon="info",
                color_scheme="blue",
                size="1",
                margin_bottom="1rem",
            ),
        ),
        # Host
        _field(
            "Host",
            rx.hstack(
                rx.input(
                    value=State.working_platform.host.ansible_host,
                    on_change=lambda v: State.update_detail("id", v),
                    on_blur=State.determine_host_reachability(State.working_platform),
                    color_scheme=rx.cond(State.is_host_resolvable, "gray", "red"),
                    size="2",
                    width="100%",
                ),
                rx.cond(
                    State.host_pinging,
                    rx.spinner(size="2"),
                    rx.cond(
                        State.is_host_resolvable,
                        rx.icon("check", size=16, color="var(--green-9)"),
                        rx.icon("triangle-alert", size=16, color="var(--red-9)"),
                    ),
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            required=True,
            error=rx.cond(
                State.is_host_resolvable == False,
                rx.text("Host must be a valid domain or IP address", size="1", color="var(--red-9)", padding_left="183px"),
                rx.fragment(),
            ),
        ),
        _divider(),
        # Username
        _field(
            "Username",
            rx.input(
                value=State.working_platform.host.ansible_user,
                on_change=lambda v: State.update_detail("ansible_user", v),
                size="2",
                width="100%",
            ),
            tooltip="SSH username on the remote host. Must have sudo permissions.",
            required=True,
        ),
        # SSH Port (hidden in local mode)
        rx.cond(
            ~is_local,
            rx.fragment(
                _divider(),
                _field(
                    "SSH Port",
                    rx.input(
                        value=State.working_platform.host.ansible_port,
                        on_change=lambda v: State.update_detail("ansible_port", v),
                        size="2",
                        width="100%",
                    ),
                    tooltip="SSH port on the remote host (default: 22)",
                    required=True,
                    error=rx.cond(
                        State.connection_ansible_port_validity == False,
                        rx.text("Port must be a valid port number", size="1", color="var(--red-9)", padding_left="183px"),
                        rx.fragment(),
                    ),
                ),
            ),
        ),
        # Advanced settings
        _divider(),
        rx.accordion.root(
            rx.accordion.item(
                header=rx.hstack(
                    rx.icon("chevrons-down", size=14, color="var(--gray-9)"),
                    rx.text("Advanced Settings", size="2", color="var(--gray-10)"),
                    spacing="2",
                    align="center",
                ),
                value="advanced",
                content=rx.vstack(
                    _field("HTTP Proxy",
                        rx.input(value=State.working_platform.host.http_proxy,
                                 on_change=lambda v: State.update_detail("http_proxy", v), size="2", width="100%"),
                        tooltip="Optional HTTP proxy (e.g. http://proxy:8080)"),
                    _divider(),
                    _field("HTTPS Proxy",
                        rx.input(value=State.working_platform.host.https_proxy,
                                 on_change=lambda v: State.update_detail("https_proxy", v), size="2", width="100%"),
                        tooltip="Optional HTTPS proxy (e.g. https://proxy:8080)"),
                    _divider(),
                    _field("VOLTTRON Home",
                        rx.input(value=State.working_platform.host.volttron_home,
                                 on_change=lambda v: State.update_detail("volttron_home", v),
                                 placeholder="~/.volttron", size="2", width="100%"),
                        tooltip="Directory where VOLTTRON stores data and config (default: ~/.volttron)"),
                    _divider(),
                    _field("VOLTTRON venv",
                        rx.input(value=State.working_platform.host.volttron_venv,
                                 on_change=lambda v: State.update_detail("volttron_venv", v),
                                 placeholder="~/volttron.venv", size="2", width="100%"),
                        tooltip="Python virtual environment path (default: ~/volttron.venv)"),
                    _divider(),
                    _field("VOLTTRON Source",
                        rx.input(value=State.working_platform.host.volttron_source,
                                 on_change=lambda v: State.update_detail("volttron_source", v),
                                 placeholder="~/volttron", size="2", width="100%"),
                        tooltip="Source code path for monolithic installs only"),
                    _divider(),
                    _field("Custom Python",
                        rx.input(value=State.working_platform.platform.config.custom_python_path,
                                 on_change=lambda v: State.update_platform_config_detail("custom_python_path", v),
                                 placeholder="e.g. ~/.pyenv/versions/3.10.14/bin/python3", size="2", width="100%"),
                        tooltip="Custom Python 3.10 executable path. Leave empty for auto-detection."),
                    rx.cond(
                        ~is_local,
                        rx.fragment(
                            _divider(),
                            _field("Ignore Host Keys",
                                rx.checkbox(
                                    checked=State.working_platform.host.ignore_host_keys,
                                    on_change=lambda v: State.update_detail("ignore_host_keys", v),
                                    size="2",
                                ),
                                tooltip="Skip SSH host key verification (StrictHostKeyChecking=no). Less secure but useful for initial setup."),
                        ),
                    ),
                    spacing="0",
                    align="start",
                    width="100%",
                    padding_top="1rem",
                ),
            ),
            collapsible=True,
            variant="ghost",
            width="100%",
        ),
    )


# ─── Instance section ────────────────────────────────────────────────────────

def _instance_section() -> rx.Component:
    return _section(
        "Instance Configuration", "settings",
        # Instance Name
        _field(
            "Instance Name",
            rx.input(
                value=State.working_platform.platform.config.instance_name,
                on_change=lambda v: State.update_platform_config_detail("instance_name", v),
                size="2",
                width="100%",
            ),
            tooltip="Unique name for this platform. Letters, numbers, hyphens, and underscores only.",
            required=True,
            error=rx.vstack(
                rx.cond(
                    State.platform_instance_name_validity == False,
                    rx.text("Must contain only letters, numbers, hyphens, and underscores", size="1", color="var(--red-9)", padding_left="183px"),
                    rx.fragment(),
                ),
                rx.cond(
                    State.platform_instance_name_not_in_use == False,
                    rx.text("Instance name already in use", size="1", color="var(--red-9)", padding_left="183px"),
                    rx.fragment(),
                ),
                spacing="0",
                align="start",
                width="100%",
            ),
        ),
        _divider(),
        # VOLTTRON Type
        _field(
            "Type",
            rx.vstack(
                rx.hstack(
                    rx.button("Modular",
                        on_click=lambda: State.update_platform_config_detail("volttron_type", "modular"),
                        variant=rx.cond(State.working_platform.platform.config.volttron_type == "modular", "solid", "soft"),
                        color_scheme=rx.cond(State.working_platform.platform.config.volttron_type == "modular", "blue", "gray"),
                        size="2", style={"flex": "1"}),
                    rx.button("Monolithic",
                        on_click=lambda: State.update_platform_config_detail("volttron_type", "monolithic"),
                        variant=rx.cond(State.working_platform.platform.config.volttron_type == "monolithic", "solid", "soft"),
                        color_scheme=rx.cond(State.working_platform.platform.config.volttron_type == "monolithic", "blue", "gray"),
                        size="2", style={"flex": "1"}),
                    spacing="2",
                    width="100%",
                ),
                rx.text(
                    rx.cond(
                        State.working_platform.platform.config.volttron_type == "modular",
                        "Agents are pip packages installed independently — modern and easy to maintain.",
                        "All-in-one installation with agents bundled — traditional approach.",
                    ),
                    size="1",
                    color="var(--gray-9)",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            tooltip="Modular (recommended): pip-based agents. Monolithic: bundled all-in-one.",
        ),
        # Version (modular only)
        rx.cond(
            State.working_platform.platform.config.volttron_type == "modular",
            rx.fragment(
                _divider(),
                _field(
                    "Version",
                    rx.input(
                        value=State.working_platform.platform.config.volttron_version,
                        on_change=lambda v: State.update_platform_config_detail("volttron_version", v),
                        placeholder="e.g. 2.0.0rc20  (leave blank for latest)",
                        size="2",
                        width="100%",
                    ),
                    tooltip="Leave blank for latest PyPI release. Or: 2.0.0rc20, user/repo@branch, git+https://...",
                ),
            ),
        ),
        _divider(),
        # VIP Address
        _field(
            "VIP Address",
            rx.input(
                value=State.working_platform.platform.config.vip_address,
                on_change=lambda v: State.update_platform_config_detail("vip_address", v),
                size="2",
                width="100%",
            ),
            tooltip="VOLTTRON Interconnect Protocol address. Format: tcp://<ip>:<port>",
            required=True,
            error=rx.cond(
                State.platform_vip_address_validity == False,
                rx.text("Must be in the format tcp://<ip>:<port>", size="1", color="var(--red-9)", padding_left="183px"),
                rx.fragment(),
            ),
        ),
        _divider(),
        # Web Interface toggle
        rx.hstack(
            rx.checkbox(
                checked=State.working_platform.web_checked,
                on_change=State.toggle_web,
                size="2",
            ),
            rx.vstack(
                rx.text("Enable Web Interface", size="2", weight="medium", color="var(--gray-11)"),
                rx.text("Browser-based platform management and monitoring", size="1", color="var(--gray-9)"),
                spacing="0",
                align="start",
            ),
            spacing="2",
            align="start",
        ),
        rx.cond(
            State.working_platform.web_checked,
            rx.box(
                _field(
                    "Web Bind Address",
                    rx.input(
                        value=State.working_platform.web_bind_address,
                        on_change=lambda v: State.update_platform_config_detail("web_bind_address", v),
                        placeholder="https://0.0.0.0:8443",
                        size="2",
                        width="100%",
                    ),
                    tooltip="Address and port for the web interface (e.g. https://0.0.0.0:8443)",
                ),
                padding_left="1.5rem",
                padding_top="0.75rem",
                border_left="2px solid var(--accent-5)",
                margin_top="0.75rem",
                margin_left="0.25rem",
                width="100%",
            ),
        ),
        _divider(),
        # Federation toggle
        rx.hstack(
            rx.checkbox(
                size="2",
                on_click=State.toggle_federation,
            ),
            rx.vstack(
                rx.text("Join a Federation", size="2", weight="medium", color="var(--gray-11)"),
                rx.text("Connect this platform to a multi-platform VOLTTRON federation", size="1", color="var(--gray-9)"),
                spacing="0",
                align="start",
            ),
            spacing="2",
            align="start",
        ),
    )


# ─── Agents section ──────────────────────────────────────────────────────────

def _agents_section() -> rx.Component:
    return _section(
        "Pre-Deployment Agents", "bot",
        rx.text(
            "Add agents that will be installed when this platform is deployed. You can also add or remove agents later from the Overview tab.",
            size="2",
            color="var(--gray-9)",
            margin_bottom="1rem",
        ),
        rx.hstack(
            # Available
            rx.vstack(
                rx.text("Available", size="2", weight="bold", color="var(--gray-11)", margin_bottom="0.5rem"),
                rx.vstack(
                    rx.foreach(
                        State.list_of_agents,
                        lambda agent, index: rx.hstack(
                            rx.text(agent.identity, size="2", color="var(--gray-12)", flex="1"),
                            rx.icon_button(
                                rx.icon("plus", size=14),
                                size="1",
                                variant="soft",
                                on_click=State.handle_adding_agent(agent, State.current_uid),
                            ),
                            spacing="2",
                            align="center",
                            width="100%",
                            padding="0.4rem 0.6rem",
                            border_radius="6px",
                            background="var(--gray-2)",
                        ),
                    ),
                    spacing="1",
                    align="start",
                    width="100%",
                ),
                align="start",
                flex="1",
                min_width="200px",
            ),
            # Separator
            rx.divider(orientation="vertical", height="auto", min_height="100px"),
            # Added
            rx.vstack(
                rx.text("Selected", size="2", weight="bold", color="var(--gray-11)", margin_bottom="0.5rem"),
                rx.vstack(
                    rx.foreach(
                        State.working_platform.platform.agents,
                        lambda pair: rx.hstack(
                            rx.icon_button(
                                rx.icon("trash-2", size=14),
                                size="1",
                                variant="soft",
                                color_scheme="red",
                                on_click=State.handle_removing_agent(pair[0]),
                            ),
                            rx.text(pair[1].identity, size="2", color="var(--gray-12)", flex="1"),
                            rx.icon_button(
                                rx.icon("settings", size=14),
                                size="1",
                                variant="soft",
                                on_click=NavigationState.route_to_agent_config(
                                    State.current_uid,
                                    pair[1].routing_id
                                ),
                            ),
                            spacing="2",
                            align="center",
                            width="100%",
                            padding="0.4rem 0.6rem",
                            border_radius="6px",
                            background="var(--gray-2)",
                        ),
                    ),
                    spacing="1",
                    align="start",
                    width="100%",
                ),
                align="start",
                flex="1",
                min_width="200px",
            ),
            spacing="4",
            align="start",
            width="100%",
        ),
    )


# ─── Save / Cancel bar ───────────────────────────────────────────────────────

def _action_bar() -> rx.Component:
    deploy_btn = rx.cond(
        State.platform_deployed,
        "Save & Re-Deploy",
        "Save & Deploy",
    )
    is_disabled = ~((State.instance_savable) & (State.instance_uncaught))
    return rx.hstack(
        rx.cond(
            State.needs_password_for_deployment,
            rx.dialog.root(
                rx.dialog.trigger(
                    rx.button(deploy_btn, size="3", variant="solid", color_scheme="green", disabled=is_disabled),
                ),
                rx.dialog.content(
                    rx.dialog.title("Enter SSH Password"),
                    rx.dialog.description("Enter the password for SSH connection to deploy the platform.", size="2", mb="4"),
                    rx.flex(
                        rx.input(
                            value=State.working_platform.password,
                            on_change=State.update_password_field,
                            type="password",
                            placeholder="SSH password",
                        ),
                        rx.flex(
                            rx.dialog.close(rx.button("Cancel", variant="soft", color_scheme="gray")),
                            rx.dialog.close(rx.button("Deploy", on_click=State.handle_save, color_scheme="green")),
                            spacing="3",
                            mt="4",
                            justify="end",
                        ),
                        direction="column",
                        spacing="3",
                    ),
                ),
            ),
            rx.button(deploy_btn, size="3", variant="solid", color_scheme="green",
                      on_click=State.handle_save, disabled=is_disabled),
        ),
        rx.button(
            "Cancel",
            size="3",
            variant="soft",
            color_scheme="gray",
            on_click=State.handle_cancel,
            disabled=~State.instance_uncaught,
        ),
        spacing="3",
        padding_top="1rem",
        justify="end",
        width="100%",
    )


# ─── Main export ─────────────────────────────────────────────────────────────

def configuration_tab_content() -> rx.Component:
    return rx.cond(
        State.is_hydrated,
        rx.vstack(
            _connection_section(),
            _instance_section(),
            _agents_section(),
            _action_bar(),
            spacing="4",
            align="start",
            width="100%",
            max_width="760px",
            margin="0 auto",
        ),
    )

