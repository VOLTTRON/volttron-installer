# hosts_tab.py

# heres the plan, so we create a base ccomponent state or soemthing like taht and thne we 
# have a list of thos inside of HostsTabState then we iterate through that to then make
# our stuff from that list of classes. for instance, we call the .form() function or whatever
# and its just there chillin for us to use

# def craft_form_from_data(component_id: str) -> rx.Component:
#     return hosts.host_form(component_id)


# def craft_tile_from_data(host: typing.List) -> rx.Component:
#     component_id = host[0]

#     return form_components.form_selection_button.form_selection_button(
#         # text="",
#         text=rx.cond(
#             state.HostsTabState.committed_host_forms.contains(component_id),
#             state.HostsTabState.committed_host_forms[component_id]["host_id"],
#             ""
#         ),
#         selection_id=component_id,
#         selected_item=state.HostsTabState.selected_id,
#         on_click = state.HostsTabState.handle_selected_tile(component_id),
#         delete_component=delete_icon_button.delete_icon_button()
#     )


# def host_tab() -> rx.Component:
#     return form_components.form_tab.form_tab(
#         form_components.form_tile_column.form_tile_column_wrapper(
#             setup_button.setup_button(
#                 "Create a Host",
#                 on_click = lambda : state.HostsTabState.generate_new_form_tile()
#             ),
#             rx.foreach(
#                 state.HostsTabState.host_forms,
#                 craft_tile_from_data
#             )
#         ),
#         form_components.form_view.form_view_wrapper(
#             rx.cond(
#                 state.HostsTabState.selected_id != "",
#                 rx.cond(
#                     state.HostsTabState.host_forms.contains(state.HostsTabState.selected_id),
#                     craft_form_from_data(state.HostsTabState.selected_id),
#                     # rx.text(HostsTabState.selected_id),
#                     rx.text("Invalid host selected")
#                 ),
#                 rx.text("Select a host to view or edit")
#             )
#         )
#     )

import reflex as rx
from .. import form_components
from ..configuring_components import hosts
from . import base, state, tab_states
from .tab_states import HostTab, HostTabContent
from ..buttons import setup_button, delete_icon_button
from .host_tab.configure_host import host_form

def funky(tab_content: HostTabContent) -> rx.Component:
    return rx.text(f"dr faciiii, give us vaceenics, {tab_content.tab_content_id}")

def craft_form_from_data(host_tab_content: HostTabContent) -> rx.Component:
    return host_form(host_tab_content)
    # return rx.text(f"dr faciiii, give us vaceenics, {host_tab_content.tab_content_id}")
    # return funky(host_tab_content)


def craft_tile_from_data(host_tab_content: HostTabContent) -> rx.Component:
    host_tab_content_id = host_tab_content.tab_content_id

    return form_components.form_selection_button.form_selection_button(
        text=rx.cond(
                host_tab_content.committed,
                host_tab_content.host_entry.host_id,
                ""
            ),
        selection_id=host_tab_content_id,
        selected_item=HostTab.selected_id,
        on_click = HostTab.refresh_selected_id(host_tab_content_id),
        delete_component=delete_icon_button.delete_icon_button()
    )


def host_tab() -> rx.Component:
    return form_components.form_tab.form_tab(
        form_components.form_tile_column.form_tile_column_wrapper(
            setup_button.setup_button(
                "Create a Host",
                on_click = lambda : HostTab.append_new_content()
            ),
            rx.foreach(
                HostTab.list_of_host_tab_content,
                craft_tile_from_data
            )
        ),
        form_components.form_view.form_view_wrapper(
            rx.cond(
                HostTab.selected_id != "",
                # finding broo
                # rx.text("bruhs house"),
                rx.foreach(
                    HostTab.list_of_host_tab_content,
                    lambda host_tab_content: rx.cond(
                            HostTab.selected_id == host_tab_content.tab_content_id,
                            craft_form_from_data(host_tab_content),
                            # rx.text(HostsTabState.selected_id),
                        ),
                ),
                rx.text("Select a host to view or edit")
            )
        )
    )