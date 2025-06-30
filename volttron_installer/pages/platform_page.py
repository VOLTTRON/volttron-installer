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

@rx.page(route="/platform/[uid]", on_load=State.hydrate_state)
def platform_page() -> rx.Component:

    working_platform: Instance = State.platforms[State.current_uid]

    return rx.cond(
        State.is_hydrated, 
        rx.fragment(
            app_layout(
                header(
                rx.hstack(
                    icon_button_wrapper.icon_button_wrapper(
                        tool_tip_content="Go back to overview",
                        icon_key="arrow-left",
                        on_click=lambda: NavigationState.route_to_index()
                    ),
                    rx.text(f"""{
                            rx.cond(
                                working_platform.new_instance,
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
                        working_platform.new_instance==False,
                        icon_button_wrapper.icon_button_wrapper(
                            tool_tip_content="Copy Platform",
                            icon_key="copy",
                            on_click=lambda: State.copy_platform(State.current_uid)
                        )
                    ),
                    icon_button_wrapper.icon_button_wrapper(
                        tool_tip_content="Delete platform",
                        icon_key="trash-2",
                    ),
                ),
                justify="between"
            ),
            platform_tabs()
            )
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
#   working_platform: Instance = State.platforms[State.current_uid]
#   return rx.cond(State.is_hydrated,
#             rest of component...
#             )


def platform_tabs() -> rx.Component:
    working_platform: Instance = State.platforms[State.current_uid]
    return rx.cond(
        State.is_hydrated,
        rx.box(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        "Status", value="status", disabled=rx.cond(
                            working_platform.platform.in_file,
                            False,
                            True
                        )
                    ),
                    rx.tabs.trigger("Configuration", value="configuration"),
                ),
                rx.tabs.content(
                    data_tab_content(),
                    value="status"
                ),
                rx.tabs.content(
                    rx.box(
                        configuration_tab_content(),
                        padding="1rem"
                    ),
                    value="configuration"
                ),
                default_value=rx.cond(
                    working_platform.platform.in_file,
                    "status",
                    "configuration"
                )
            )
        )
    )

# Config tab and it's components:
def configuration_tab_content() -> rx.Component:
    working_platform: Instance = State.platforms[State.current_uid]
    
    return rx.cond(State.is_hydrated, 
            rx.box(
                rx.accordion.root(
                    rx.accordion.item(
                        header="Connection",
                        value="connection",
                        # content=rx.box(
                        #     connection_accordion_content(working_platform)
                        # ),
                        content=rx.box(
                            rx.box(
                                form_entry.form_entry(
                                    "Host",
                                    rx.input(
                                        value= working_platform.host.ansible_host,
                                        on_change=lambda v: State.update_detail("id", v),
                                        size="3",
                                        required=True,
                                        on_blur=lambda: State.determine_host_reachability(working_platform),
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
                                        value= working_platform.host.ansible_user,
                                        on_change=lambda v: State.update_detail("ansible_user", v),
                                        size="3",
                                        required=True,
                                    ),
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="Username must have SUDO permissions"
                                    ),
                                    required_entry=True,
                                ),
                                form_entry.form_entry(
                                    "Port SSH",
                                    rx.input(
                                        value= working_platform.host.ansible_port,
                                        on_change=lambda v: State.update_detail("ansible_port", v),
                                        size="3",
                                        required=True,
                                    ),
                                    required_entry=True,
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
                                            working_platform.advanced_expanded,
                                            rx.icon("chevron-up"),
                                            rx.icon("chevron-down")
                                        )
                                    ),
                                    class_name="toggle_advanced_button",
                                    on_click=lambda: State.toggle_advanced(State.current_uid)
                                ),
                                rx.cond(
                                    working_platform.advanced_expanded,
                                    rx.fragment(
                                        form_entry.form_entry(
                                            "HTTP Proxy",
                                            rx.input(
                                                value= working_platform.host.http_proxy,
                                                on_change=lambda v: State.update_detail("http_proxy", v),
                                                size="3",
                                                required=True,
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "HTTPS Proxy",
                                            rx.input(
                                                value= working_platform.host.https_proxy,
                                                on_change=lambda v: State.update_detail("https_proxy", v),
                                                size="3",
                                                required=True,
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "VOLTTRON Home",
                                            rx.input(
                                                value= working_platform.host.volttron_home,
                                                on_change=lambda v: State.update_detail("volttron_home", v),
                                                size="3",
                                                required=True,
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
                        #     instance_configuration_accordion_content(working_platform)
                        # ),
                        content=rx.box(
                            rx.box(
                                form_entry.form_entry( # validate
                                    "Instance Name",
                                    rx.vstack(
                                        rx.input(
                                            size="3",
                                            value=working_platform.platform.config.instance_name,
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
                                form_entry.form_entry( # validate
                                    "Vip Address",
                                    rx.vstack(
                                        rx.input(
                                            size="3",
                                            value=working_platform.platform.config.vip_address,
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
                                        tooltip="Vip Address must be in the format tcp://<ip>:<port>"
                                    )
                                ),
                                form_entry.form_entry(
                                    "Member of Federation",
                                    rx.vstack(
                                        rx.checkbox(
                                            size="3",
                                            on_click = lambda: State.toggle_federation()
                                        ),
                                        justify="center",
                                        align="center",
                                        width="100%"
                                    )
                                ),
                                form_entry.form_entry(
                                    "Web",
                                    rx.vstack(
                                        rx.checkbox(
                                            size="3",
                                            checked=working_platform.web_checked,
                                            on_change=lambda: State.toggle_web()
                                        ),
                                        justify="center",
                                        align="center",
                                        width="100%"
                                    )
                                ),
                                rx.cond(
                                    working_platform.web_checked,
                                    rx.fragment(
                                        form_entry.form_entry(
                                            "Web Bind Address",
                                            rx.input(
                                                size="3",
                                                value=working_platform.web_bind_address,
                                                on_change=lambda v: State.update_platform_config_detail("web_bind_address", v),
                                                required=True,
                                            )
                                        )
                                    )
                                ),
                                rx.box(
                                    rx.hstack(
                                        rx.text("Agent Configuration"),
                                        rx.cond(
                                            working_platform.agent_configuration_expanded,
                                            rx.icon("chevron-up"),
                                            rx.icon("chevron-down")
                                        )
                                    ),
                                    class_name="toggle_advanced_button",
                                    on_click=lambda: State.toggle_agent_config_details()
                                ),
                                rx.box(
                                    rx.cond(
                                        working_platform.agent_configuration_expanded,
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
                                                                on_click=State.handle_adding_agent(agent)
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
                                                        working_platform.platform.agents,
                                                        lambda identity_agent_pair: config_tile.config_tile(
                                                            identity_agent_pair[1].identity,
                                                            left_component=tile_icon(
                                                                "trash-2",
                                                                on_click= lambda: State.handle_removing_agent(identity_agent_pair[0])
                                                                # on_click= lambda: State.handle_removing_agent(identity_agent_pair[0])
                                                            ),
                                                            right_component=tile_icon(
                                                                "settings",
                                                                on_click=lambda: NavigationState.route_to_agent_config(
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
                        on_click=lambda: State.handle_save(),
                        disabled=rx.cond(
                            (State.instance_savable)
                            & (State.instance_uncaught),
                            # (working_platform.uncaught),
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
                                    rx.button(
                                        "Submit",
                                        on_click=lambda: State.handle_deploy(),
                                        disabled=rx.cond(
                                            State.password_field=="",
                                            True,
                                            False
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
                            on_click=lambda: State.handle_cancel(),
                            disabled=rx.cond(
                                State.instance_uncaught == False,
                                # working_platform.uncaught == False,
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
    return rx.cond(State.is_hydrated, rx.container(
        rx.text("this is data... in all of it's glory")
    ))


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
