import reflex as rx

def app_layout(top_component: rx.Component, form_tabs: rx.Component) -> rx.Component:
    return rx.fragment(
        top_component,
        form_tabs
    )
