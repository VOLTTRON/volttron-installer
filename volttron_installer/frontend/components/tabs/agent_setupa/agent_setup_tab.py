import reflex as rx
from ...buttons.setup_button import setup_button
from ...buttons.delete_icon_button import delete_icon_button
from ...form_components import *
from ..tab_states import AgentSetupTab, AgentTabContent
from .configure_agent import agent_setup_form
import typing


def craft_form_from_data(agent_tab_content: AgentTabContent) -> rx.Component:
    return agent_setup_form(agent_tab_content)


def craft_tile_from_data(agent_tab_content: AgentTabContent) -> rx.Component:
    
    return form_selection_button.form_selection_button(
        # instead of a blank text, we set up a cond with a chain of gets to see if the host_id is in committed forms
        text=rx.cond(
            agent_tab_content.committed,
            agent_tab_content.original_agent_entry["agent_name"],
            ""
        ),
        selection_id=agent_tab_content.tab_content_id,
        selected_item=AgentSetupTab.selected_id,
        on_click = AgentSetupTab.refresh_selected_id(agent_tab_content.tab_content_id), 
        delete_component=delete_icon_button()
    )


def agent_setup_tab() -> rx.Component:
    return form_tab.form_tab(
        form_tile_column.form_tile_column_wrapper(
            setup_button(
                "Create an Agent",
                on_click= lambda: AgentSetupTab.append_new_content()
                ),
            rx.foreach(
                AgentSetupTab.list_of_agent_tab_content,
                craft_tile_from_data
            )
        ),
        form_view.form_view_wrapper(
            rx.cond(
                AgentSetupTab.selected_id != "",
                rx.foreach(
                    AgentSetupTab.list_of_agent_tab_content,
                    lambda agent_tab_content: rx.cond(
                        AgentSetupTab.selected_id == agent_tab_content.tab_content_id,
                        craft_form_from_data(agent_tab_content)
                    )
                ),
                rx.text("Select an agent to view or edit")
            )
        )
    )