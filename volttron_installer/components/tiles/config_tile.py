import reflex as rx

def config_tile(
        text: str, 
        class_name="agent_config_tile", 
        left_component: rx.Component = False, 
        right_component: rx.Component = False, 
        tooltip: str = "",
        **props
    ) -> rx.Component:

    return rx.hstack(
        rx.cond(
            left_component,
            rx.flex(
                left_component,
                align="center",
                justify="center",
            )
        ),
        rx.cond(
            tooltip != "",
            rx.tooltip(
                rx.flex(
                    rx.text(text, white_space="normal"),
                    class_name=class_name,
                ),
                content=tooltip
            ),
            rx.flex(
                rx.text(text, white_space="normal"),
                class_name=class_name,
            ),
        ),
        rx.cond(
            right_component,
            rx.flex(
                right_component,
                align="center",
                justify="center"
            )
        ),
        spacing="2",
        align="center",
        **props,
    )