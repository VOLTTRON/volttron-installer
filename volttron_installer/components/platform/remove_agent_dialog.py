import reflex as rx
from ...state import PlatformPageState as State

def remove_agent_dialog() -> rx.Component:
    """Dialog for confirming agent removal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Remove Agent"),
            rx.dialog.description(
                "Are you sure you want to remove this agent? This action cannot be undone."
            ),
            rx.flex(
                rx.dialog.close(
                    rx.button("Cancel", variant="soft", color_scheme="gray"),
                ),
                rx.dialog.close(
                    rx.button(
                        "Remove Agent",
                        on_click=State.confirm_remove_agent,
                        color_scheme="red",
                    ),
                ),
                spacing="3",
                justify="end",
            ),
        ),
        open=State.show_remove_agent_dialog,
        on_open_change=State.close_remove_agent_dialog,
    )
