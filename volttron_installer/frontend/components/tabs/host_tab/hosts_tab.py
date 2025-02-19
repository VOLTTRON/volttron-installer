
import reflex as rx
from ... import form_components
from ...configuring_components import hosts
from ..tab_states import HostTab, HostTabContent
from ...buttons import setup_button, delete_icon_button
from ..host_tab.configure_host import host_form

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
                host_tab_content.original_host_entry["host_id"],
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