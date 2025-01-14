import reflex as rx
import typing

def form_tab(section_1: typing.Callable[[], rx.Component], section_2: typing.Callable[[], rx.Component]) -> rx.Component:

    return rx.flex(
        section_1,
        rx.divider(orientation="vertical", size="4"),
        section_2,
        direction="row",
        # align="baseline"
    )