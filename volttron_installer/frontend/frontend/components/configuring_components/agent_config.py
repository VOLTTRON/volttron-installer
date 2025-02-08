import reflex as rx
from ..form_components import *
from ..buttons import upload_button, setup_button, delete_icon_button
from ..custom_fields import text_editor
from ..tabs.state import AgentSetupTabState, PlatformOverviewState, PlatformState



def render_config_form(agent_component_id: str, platform_uid: str) -> rx.Component:
    return rx.form(
            form_view.form_view_wrapper(
                form_entry.form_entry(
                    "Agent Config",
                    text_editor.text_editor(
                        value=PlatformOverviewState.platforms[platform_uid][agent_component_id]["agent_config"],
                        # one sec, how do we get the agent_name?
                        on_change = lambda v: PlatformOverviewState.update_form_field(platform_uid, agent_component_id, v)
                        # on_change = PlatformOverviewState.platforms[platform_uid][data[0]]["agent_config"]
                    ),
                    upload=rx.upload.root(
                        upload_button.upload_button(),
                        accept={
                            "file/json" : [".json"],
                            "file/yaml" : [".yaml"],
                        }
                    )
                )
            )
        )


def craft_form_tile(agent_component_id: str, platform_uid: str) -> rx.Component:
    return form_selection_button.form_selection_button(
            text="",
            selection_id=agent_component_id,
            selected_item=PlatformOverviewState.selected_agent_component_id,
            on_click=PlatformOverviewState.handle_selected_agent(agent_component_id),
            delete_component=delete_icon_button.delete_icon_button()
        )

# holes here, regarding the component_id

def agent_config_form( platform_uid: str ) -> rx.Component:
    return form_tab.form_tab(
        form_tile_column.form_tile_column_wrapper(
            rx.form(
                rx.hstack(
                    rx.select(
                        AgentSetupTabState.committed_agents_list,
                        required=True,
                        name="agent_name"
                    ),
                    setup_button.setup_button(
                        "Add",
                        type="submit"
                    ),
                ),
                on_submit = lambda data: PlatformOverviewState.add_agent(data, platform_uid)
            ),
            rx.foreach(
                PlatformOverviewState.agents_added_list[platform_uid],
                lambda agent_component_id: craft_form_tile(agent_component_id, platform_uid)
            )
        ),
        form_view.form_view_wrapper(
            rx.cond(
                PlatformOverviewState.selected_agent_component_id !="",
                # rx.cond(
                    # PlatformOverviewState.platforms[platform_uid]["agents"].contains(PlatformOverviewState.selected_agent_component_id),
                    rx.box()
                    # render_config_form()

                # )
            )
        )
        # rx.foreach(
        #     PlatformOverviewState.agents_added_list,
        #     lambda agent_component_id: render_config_form(agent_component_id, platform_uid) 
        # )
    )
