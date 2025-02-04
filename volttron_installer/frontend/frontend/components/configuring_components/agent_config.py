import reflex as rx
from ..form_components import *
from ..buttons import upload_button, setup_button
from ..custom_fields import text_editor
from ..tabs.state import AgentSetupTabState, PlatformOverviewState, PlatformState

def render_config_form(data: tuple, platform_uid: str) -> rx.Component:
    return rx.form(
            form_view.form_view_wrapper(
                form_entry.form_entry(
                    "Agent Config",
                    text_editor.text_editor(
                        value=PlatformOverviewState.platforms[platform_uid][data[0]]["agent_config"],
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


#plot holes here, regarding the component_id

def agent_config_form( platform_uid: str ) -> rx.Component:
    return form_tab.form_tab(
        form_tile_column.form_tile_column_wrapper(
            rx.form(
                rx.hstack(
                    rx.select(
                        AgentSetupTabState.committed_agents_list,
                        required=True,
                        name="agent_to_add"
                    ),
                    setup_button.setup_button(
                        "Add",
                        type="submit"
                    ),
                    #on_submit = lambda data: platform.add_agent_to_agents_dict(data, platform_id)
                )
            ),
        ),
        rx.foreach(
            PlatformOverviewState.platforms[platform_uid]["agents"],
            lambda data: render_config_form(data, platform_uid) 
        )
    )
