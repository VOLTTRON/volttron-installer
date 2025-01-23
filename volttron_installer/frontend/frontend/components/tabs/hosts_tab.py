# hosts_tab.py
import reflex as rx
from .. import form_components
from ..configuring_components import hosts
from . import base, state
import typing
import random
from ..buttons import setup_button
# heres the plan, so we create a base ccomponent state or soemthing like taht and thne we 
# have a list of thos inside of HostsTabState then we iterate through that to then make
# our stuff from that list of classes. for instance, we call the .form() function or whatever
# and its just there chillin for us to use


def craft_form_from_data(component_id: str) -> rx.Component:
    return hosts.host_form(component_id)


def craft_tile_from_data(host: typing.List) -> rx.Component:
    return form_components.form_selection_button.form_selection_button(
        text="",
        selection_id=host[0],
        selected_item=state.HostsTabState.selected_id,
        on_click = state.HostsTabState.handle_selected_tile(host[0]),
    )


def host_tab() -> rx.Component:
    return form_components.form_tab.form_tab(
        form_components.form_tile_column.form_tile_column_wrapper(
            setup_button.setup_button(
                "Add Host",
                on_click = lambda : state.HostsTabState.generate_new_form_tile()
            ),
            rx.foreach(
                state.HostsTabState.host_forms,
                craft_tile_from_data
            )
        ),
        form_components.form_view.form_view_wrapper(
            rx.cond(
                state.HostsTabState.selected_id != "",
                rx.cond(
                    state.HostsTabState.host_forms.contains(state.HostsTabState.selected_id),
                    craft_form_from_data(state.HostsTabState.selected_id),
                    # rx.text(HostsTabState.selected_id),
                    rx.text("Invalid host selected")
                ),
                rx.text("Select a host to view or edit")
            )
        )
    )