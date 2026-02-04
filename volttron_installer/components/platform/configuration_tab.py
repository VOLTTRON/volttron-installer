import reflex as rx
from ...state import PlatformPageState as State
from ...components.form_components import form_entry
from ...components.buttons.tile_icon import tile_icon
from ...components.tiles import config_tile
from ...navigation.state import NavigationState

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
