import reflex as rx
from ..layouts.app_layout import app_layout
from ..model_views import AgentModelView, ConfigStoreEntryModelView
from ..components.header.header import header
from ..components.buttons import icon_button_wrapper, icon_upload, tile_icon
from ..components.form_components import *
from ..components.custom_fields import text_editor, csv_field
from ..components.tiles.config_tile import config_tile
from ..utils.create_component_uid import generate_unique_uid
from .platform_page import State as AppState
from .platform_page import Instance
from ..navigation.state import NavigationState
from ..utils.conversion_methods import json_string_to_csv_string, csv_string_to_json_string, identify_string_format, csv_string_to_usable_dict
from ..utils.validate_content import check_json, check_csv, check_path, check_yaml, check_regular_expression
from ..utils.create_csv_string import create_csv_string, create_and_validate_csv_string
from ..state import AgentConfigState
import io, re, json, csv, yaml
from loguru import logger

@rx.page(route="/platform/[uid]/agent/[agent_uid]", on_load=AgentConfigState.hydrate_working_agent)
def agent_config_page() -> rx.Component:
    return rx.cond(
        AgentConfigState.is_hydrated, 
        app_layout(
            header(
                icon_button_wrapper.icon_button_wrapper(
                    tool_tip_content="Go back to platform",
                    icon_key="arrow-left",
                    on_click=lambda: NavigationState.route_back_to_platform(
                        AgentConfigState.agent_details["uid"]
                    )
                ),
                rx.hstack(
                    rx.heading(
                        rx.cond(
                            AgentConfigState.working_agent.safe_agent["identity"] != "",
                            AgentConfigState.working_agent.safe_agent["identity"],
                            "New Agent"
                        ), 
                        trim="both",
                        as_="h3"
                    ),
                    rx.button(
                        "Save Agent",
                        variant="soft",
                        color_scheme="green",
                        on_click = AgentConfigState.flip_draft_visibility,
                        disabled = rx.cond(
                            AgentConfigState.agent_valid,
                            False,
                            True
                        )
                    ),
                    spacing="6",
                    align="center"
                    ),
            ),
            rx.flex(
                agent_draft(),
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Agent Config", value="1"),
                        rx.tabs.trigger("Config Store Entries", value="2", disabled=rx.cond(AgentConfigState.working_agent.config_store_allowed, False, True))
                    ),
                    rx.tabs.content(
                        agent_config_tab(),
                        value="1"
                    ),
                    rx.tabs.content(
                        rx.flex(
                            rx.flex(
                                rx.flex(
                                    rx.hstack(
                                        tile_icon.tile_icon(
                                            "plus",
                                            tooltip="Create a new config store entry",
                                            on_click=AgentConfigState.create_blank_config_entry
                                        ),
                                        rx.upload.root(
                                            tile_icon.tile_icon(
                                                "upload",
                                                tooltip="Upload a CSV or JSON file",
                                            ),
                                            id="config_store_entry_upload",
                                            accept={
                                                "text/csv": [".csv"],
                                                "text/json": [".json"]
                                            },
                                            on_drop=AgentConfigState.handle_config_store_entry_upload(
                                                rx.upload_files(upload_id="config_store_entry_upload")
                                            )
                                        ),
                                        align="end",
                                        justify="end",
                                        width="100%"
                                    ),
                                    rx.divider(),
                                    rx.foreach(
                                        AgentConfigState.working_agent.config_store,
                                        lambda config: config_tile(
                                            text=config.path,
                                            left_component=tile_icon.tile_icon(
                                                "trash-2",
                                                class_name="icon_button delete",
                                                on_click=lambda: AgentConfigState.delete_config_store_entry(config)
                                            ),
                                            right_component=tile_icon.tile_icon(
                                                "settings",
                                                class_name=rx.cond(
                                                    AgentConfigState.working_agent.selected_config_component_id == config.component_id,
                                                    "icon_button active",  # Combined class names
                                                    "icon_button"
                                                ),
                                                on_click=lambda: AgentConfigState.set_component_id(config.component_id)
                                            ),
                                            #TODO, i would like to create a system to check if the config is changed or not, apparently we cant index the 
                                            # dict which is annoying....
                                            class_name=rx.cond(
                                                AgentConfigState.changed_configs_list.contains(config.component_id),
                                                "agent_config_tile uncommitted",
                                                "agent_config_tile"
                                            ),
                                            tooltip=rx.cond(
                                                AgentConfigState.changed_configs_list.contains(config.component_id),
                                                "Config store entry has unsaved changes",
                                                ""
                                            ),
                                        )
                                    ),
                                    direction="column",
                                    flex="1",
                                    align="start",
                                    spacing="4",
                                    justify="start",
                                ),
                                border_radius=".5rem",
                                padding="1rem",
                            ),
                            rx.flex(
                                rx.flex(
                                    rx.cond(
                                        AgentConfigState.working_agent.selected_config_component_id != "",
                                        rx.fragment(
                                            rx.foreach(
                                                AgentConfigState.working_agent.config_store,
                                                lambda config: rx.cond(
                                                    config.component_id == AgentConfigState.working_agent.selected_config_component_id,
                                                    rx.fragment(
                                                        form_view.form_view_wrapper(
                                                            form_entry.form_entry(
                                                                #TODO need to fix this weird warping stuff with the upload component
                                                                "Path",
                                                                rx.vstack(
                                                                    rx.input(
                                                                        size="3",
                                                                        value=config.path,
                                                                        on_change=lambda v: AgentConfigState.update_config_detail("path", v),
                                                                        color_scheme=rx.cond(
                                                                            AgentConfigState.path_validity == False,
                                                                            "red",
                                                                            "gray"
                                                                        ),
                                                                    ),
                                                                    rx.cond(
                                                                        AgentConfigState.path_validity == False,
                                                                        rx.text(
                                                                            "Path must start with a letter and can only contain letters, numbers, underscores, periods, or hyphens.",
                                                                            color_scheme="red"
                                                                        )
                                                                    )
                                                                ),
                                                                required_entry=True
                                                            ),
                                                            form_entry.form_entry(
                                                                "Data Type",
                                                                rx.radio(
                                                                    ["JSON", "CSV"],
                                                                    value=config.data_type,
                                                                    spacing="4",
                                                                    disabled=rx.cond(
                                                                        AgentConfigState.entry_config_validity == False,
                                                                        True,
                                                                        False
                                                                    ),
                                                                    on_change=lambda v: AgentConfigState.update_config_detail("data_type", v)
                                                                ),
                                                            ),
                                                            form_entry.form_entry(
                                                                "Config",
                                                                rx.cond(
                                                                    config.data_type=="JSON",
                                                                    rx.vstack(
                                                                        text_editor.text_editor(
                                                                            value=config.value,
                                                                            color_scheme=rx.cond(
                                                                                AgentConfigState.config_json_validity == False,
                                                                                "red",
                                                                                "gray"
                                                                            ),
                                                                            on_change=lambda v: AgentConfigState.update_config_detail("value", v)
                                                                        ),
                                                                        rx.cond(
                                                                            AgentConfigState.config_json_validity == False,
                                                                            rx.text(
                                                                                "Invalid JSON detected",
                                                                                color_scheme="red"
                                                                            )
                                                                        )
                                                                    ),
                                                                    rx.vstack(
                                                                        csv_field.csv_data_field(
                                                                            table_width=rx.breakpoints(
                                                                                {
                                                                                    "0px" : "40vw",
                                                                                    "1200px" : "60vw"

                                                                                }
                                                                            )
                                                                        ),
                                                                        rx.cond(
                                                                            AgentConfigState.check_csv_validity == False,
                                                                            rx.text(
                                                                                "Invalid CSV variant detected",
                                                                                color_scheme="red"
                                                                            )
                                                                        ),
                                                                    )
                                                                ),
                                                            ),
                                                            rx.hstack(
                                                                rx.button(
                                                                    "Save",
                                                                    size="3",
                                                                    variant="surface",
                                                                    color_scheme="green",
                                                                    
                                                                    disabled=rx.cond(
                                                                        AgentConfigState.config_validity,
                                                                        False,
                                                                        True
                                                                    ),
                                                                    on_click=lambda: AgentConfigState.save_config_store_entry(config)
                                                                ),
                                                                # NOTE for some reason the config.changed param isn't being read,
                                                                # uncommenting the logs in the update_config_detail function shows this.
                                                                rx.cond(
                                                                    config.changed,
                                                                    rx.button(
                                                                        rx.icon("undo"),
                                                                        size="3",
                                                                        variant="surface",
                                                                        color_scheme="orange"
                                                                    ),
                                                                ),
                                                                align="center"
                                                            ),
                                                            key=config.component_id
                                                        ),
                                                    )
                                                )
                                            )
                                        ),
                                        rx.box()
                                    ),
                                    direction="column",
                                    flex="1",
                                    align="start",
                                    spacing="6",
                                ),
                                border_radius=".5rem",
                                padding="1rem",
                                flex="1",
                                width="100%"
                            ),
                            align="start",
                            spacing="6",
                            direction="row",
                            padding_top="1rem",
                        ),
                        value="2"
                    ),
                    default_value="1",
                    on_change=lambda v: AgentConfigState.change_agent_config_tab(v),
                    value=AgentConfigState.selected_tab
                ),
                direction="column",
                spacing="4",
                padding="4"
            )
        ),
        # Skeleton stuff
        rx.vstack(
            # Header
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
                rx.skeleton(
                    rx.box(),
                    height="2.5rem",
                    width="5rem",
                    radius="5rem",
                    loading=True,
                ),
                spacing="4",
                align="center",
            ),
            # Tabs divider
            rx.skeleton(
                rx.box(),
                width="100%",
                height="15px",
                loading=True,
            ),
            # Fields
            rx.vstack(
                rx.skeleton(
                    rx.box(),
                    width="4.5rem",
                    height="1.5rem",
                ),
                rx.skeleton(
                    rx.box(),
                    width="14rem",
                    height="2rem",
                ),
                spacing="4"
            ),
            rx.vstack(
                rx.skeleton(
                    rx.box(),
                    width="4.5rem",
                    height="1.5rem",
                ),
                rx.skeleton(
                    rx.box(),
                    width="14rem",
                    height="2rem",
                ),
                spacing="4"
            ),
            rx.vstack(
                rx.skeleton(
                    rx.box(),
                    width="4.5rem",
                    height="1.5rem",
                ),
                rx.skeleton(
                    rx.box(),
                    width="40rem",
                    height="25rem",
                ),
                spacing="4"
            ),
            spacing="6",
            padding="1rem",
        )
    )

def agent_draft() -> rx.Component:
    return rx.cond(AgentConfigState.is_hydrated, rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Agent Draft"),
            rx.divider(),
            rx.vstack(
                form_entry.form_entry(
                    "Identity",
                    rx.code_block(
                        AgentConfigState.working_agent.identity,
                        style={"width": "clamp(15rem, 70vw, 100%)", "overflow_x": "auto"},
                        # disabled=True
                    )
                ),
                form_entry.form_entry(
                    "Source",
                    rx.code_block(
                        AgentConfigState.working_agent.source,
                        style={"width": "clamp(15rem, 70vw, 100%)", "overflow_x": "auto"},
                    )
                ),
                form_entry.form_entry(
                    "Config",
                    rx.scroll_area(
                        rx.code_block(
                            AgentConfigState.working_agent.config,
                            language="json",
                        ),
                        scrollbars="horizontal",
                        type="auto",
                        style={"width": "clamp(15rem, 70vw, 100%)", "overflow_x": "auto"},
                    ),
                ),
                rx.cond(
                    AgentConfigState.has_valid_configs,
                    rx.fragment(
                        rx.divider(),
                        rx.heading("Config Store:", as_="h5"),
                        rx.foreach(
                            AgentConfigState.committed_configs,
                            lambda config: rx.vstack(
                                rx.divider(),
                                # Checking if our config is uncaught
                                rx.cond(
                                    AgentConfigState.changed_configs_list.contains(config.component_id),
                                    rx.container(
                                        rx.hstack(
                                            rx.icon(
                                                "triangle-alert"
                                            ),
                                            rx.text("This config has unsaved changes"),
                                            spacing="3"
                                        ),                            
                                        cursor="pointer",
                                        on_click=lambda: AgentConfigState.handle_unsaved_config_banner_click(config.component_id),
                                        background_color="#FFA726",
                                        border_radius=".75rem"
                                    )
                                ),
                                # rest of the component
                                form_entry.form_entry(
                                    "Path",
                                    rx.code_block(
                                        config.path,
                                        style={"width": "clamp(15rem, 70vw, 100%)", "overflow_x": "auto"},
                                    )
                                ),
                                form_entry.form_entry(
                                    "Data Type",
                                    rx.radio(
                                        ["JSON", "CSV"],
                                        value=config.data_type,
                                        spacing="4",
                                        disabled=True,
                                    ),
                                ),
                                form_entry.form_entry(
                                    "Config",
                                    rx.cond(
                                        config.data_type=="JSON",
                                        rx.scroll_area(
                                            rx.code_block(
                                                config.value,
                                                language="json",
                                            ),
                                            scrollbars="horizontal",
                                            type="auto",
                                            style={"width": "clamp(15rem, 70vw, 100%)", "overflow_x": "auto"},
                                        ),
                                        rx.box(
                                            rx.scroll_area(
                                                rx.code_block(
                                                    config.value,
                                                    language="csv",
                                                ),
                                                scrollbars="horizontal",
                                                type="auto",
                                                style={"width": "clamp(15rem, 70vw, 90rem)", "overflow_x": "auto"},
                                            ),
                                        )
                                    )
                                ),
                            ),
                        )
                    ),
                    rx.fragment(
                        rx.divider(),
                        rx.text("No Valid Config Store Entries."),
                    )
                ),
                rx.divider(),
                rx.cond(
                    AgentConfigState.num_of_new_invalid_configs > 0,
                    rx.container(
                        rx.hstack(
                            rx.icon(
                                "triangle-alert"
                            ),
                            # Proper grammar
                            rx.cond(
                                AgentConfigState.num_of_new_invalid_configs==1,
                                rx.text(f"1 new and unsaved config not yet considered"),
                                rx.text(f"{AgentConfigState.num_of_new_invalid_configs} new and unsaved configs not yet considered")
                            ),
                            spacing="3"
                        ),
                        background_color="#FFA726",
                        border_radius=".75rem"
                    )
                ),
                justify="center",
                spacing="6",
                margin_top="1rem",
                margin_bottom="1rem"
            ),
            rx.hstack(
                rx.button(
                    "Close",
                    variant="outline",
                    color_scheme="red",
                    on_click=AgentConfigState.flip_draft_visibility
                ),
                rx.button(
                    "Save",
                    variant="outline",
                    color_scheme="green",
                    on_click=AgentConfigState.save_agent_config
                ),
                justify="between"
            ),
            max_width="100rem",
            width="clamp(20rem, 80vw, 100rem)",
        ),
        open=AgentConfigState.draft_visible
    ))

def agent_config_tab() -> rx.Component:
    return rx.flex(
        form_entry.form_entry(
            "Identity",
            rx.vstack(
                rx.input(
                    value=AgentConfigState.working_agent.identity,
                    on_change=lambda v: AgentConfigState.update_agent_detail("identity", v),
                    size="3",
                    color_scheme = rx.cond(
                        AgentConfigState.agent_identity_validity == False,
                        "red",
                        "gray"
                    )
                ),
                rx.cond(
                    AgentConfigState.agent_identity_validity == False,
                    rx.text(
                        "Identity must start with a letter and can only contain letters, numbers, underscores, periods, or hyphens.",
                        color_scheme="red"
                    )
                ),
                rx.cond(
                    AgentConfigState.agent_identity_not_in_use == False,
                    rx.text(
                        "Identity is already in use",
                        color_scheme="red"
                    )
                )
            )
        ),
        form_entry.form_entry(
            "Source", 
            rx.vstack(
                rx.input(
                    value=AgentConfigState.working_agent.source,
                    on_change=lambda v: AgentConfigState.update_agent_detail("source", v),
                    size="3",
                    color_scheme = rx.cond(
                        AgentConfigState.agent_source_validity == False,
                        "red",
                        "gray"
                    )
                ),
                rx.cond(
                    AgentConfigState.agent_source_validity == False,
                    rx.text(
                        "Source must be a valid path",
                        color_scheme="red"
                    )
                )
            )
        ),
        form_entry.form_entry(
            "Agent Config",
            rx.vstack(
                text_editor.text_editor(
                    placeholder="Type out JSON, YAML, or upload a file!",
                    value=AgentConfigState.working_agent.config,
                    on_change=lambda v: AgentConfigState.update_agent_detail("config", v),
                    color_scheme = rx.cond(
                        AgentConfigState.agent_config_validity == False,
                        "red",
                        "gray"
                    ),
                ),
                rx.cond(
                    AgentConfigState.agent_config_validity == False,
                    rx.text(
                        "Invalid JSON or YAML detected",
                        color_scheme="red"
                    )
                ),
            ),
            upload=rx.upload.root( 
                icon_upload.icon_upload(),
                id="agent_config_upload",
                max_files=1,
                accept={
                    "text/yaml" : [".yml", ".yaml"],
                    "text/json" : [".json"]
                },
                on_drop=AgentConfigState.handle_agent_config_upload(
                    # agent, 
                    rx.upload_files(upload_id="agent_config_upload")
                )
            )
        ),
        direction="column",
        justify="start",
        spacing="6",
        align="start",
        padding="1rem"
    )
