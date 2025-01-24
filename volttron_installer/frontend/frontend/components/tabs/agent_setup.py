import reflex as rx
from . import state
from ..configuring_components import agent_setup
from ..buttons.setup_button import setup_button
from ..form_components import *
import typing


def craft_form_from_data(component_id: str) -> rx.Component:
    return agent_setup.agent_setup_form(component_id)


def craft_tile_from_data(data: typing.Tuple) -> rx.Component:
    component_id = data[0]
    
    return form_selection_button.form_selection_button(
        # instead of a blank text, we set up a cond with a chain of gets to see if the host_id is in committed forms
        text=rx.cond(
            state.AgentSetupTabState.committed_agent_forms.contains(component_id),
            state.AgentSetupTabState.committed_agent_forms[component_id]["agent_name"],
            ""
        ),
        selection_id=component_id,
        selected_item=state.AgentSetupTabState.selected_id,
        on_click = state.AgentSetupTabState.handle_selected_tile(component_id),
    )


def agent_setup_tab() -> rx.Component:
    return form_tab.form_tab(
        form_tile_column.form_tile_column_wrapper(
            setup_button(
                "Create an Agent",
                on_click= lambda: state.AgentSetupTabState.generate_new_form_tile()
                ),
            rx.foreach(
                state.AgentSetupTabState.agent_forms,
                craft_tile_from_data
            )
        ),
        form_view.form_view_wrapper(
            rx.cond(
                state.AgentSetupTabState.selected_id != "",
                rx.cond(
                    state.AgentSetupTabState.agent_forms.contains(state.AgentSetupTabState.selected_id),
                    craft_form_from_data(state.AgentSetupTabState.selected_id),
                    # rx.text(HostsTabState.selected_id),
                    rx.text("Invalid agent selected")
                ),
                rx.text("Select an agent to view or edit")
            )
        )
    )