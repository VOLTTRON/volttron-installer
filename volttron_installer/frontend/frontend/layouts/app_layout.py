import reflex as rx
import typing

def app_layout( top_component: typing.Callable[[], rx.Component], form_tabs: typing.Callable[[], rx.Component] ) -> rx.Component:
    
    return rx.fragment(
        top_component(),
        form_tabs()
    )
