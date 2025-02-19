import reflex as rx


def form_entry( text: str, input: rx.Component, upload: rx.Component | None = None, required_entry: bool = False) -> rx.Component:
    if upload is None:
        upload = rx.el.div()

    return rx.flex(
        rx.flex(
            rx.text(
                text,
                rx.cond(
                        required_entry,
                        rx.text.span(" *", color="red"),
                        rx.text.span("")
                    )
                ),
            upload,
            align="start",
            justify="between",
            direction="row",
            wrap="nowrap",
        ),
        rx.flex(
            input,
            direction="row"
        ),
        spacing="1",
        direction="column"
    )