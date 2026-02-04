import reflex as rx
from ...state import PlatformPageState as State

def delete_platform_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.cond(
                ~State.delete_confirmed,
                # Step 1: Delete options
                rx.vstack(
                    rx.dialog.title("Delete Platform"),
                    rx.dialog.description(
                        "Choose what to delete:",
                        size="2",
                    ),
                    rx.vstack(
                        rx.hstack(
                            rx.checkbox(
                                checked=State.delete_remote_files,
                                on_change=State.toggle_delete_remote_files,
                            ),
                            rx.vstack(
                                rx.text("Also delete VOLTTRON files on remote system", weight="medium"),
                                rx.text(
                                    "This will stop VOLTTRON, delete ~/.volttron and the virtual environment",
                                    size="1",
                                    color="gray",
                                ),
                                align="start",
                                spacing="0",
                            ),
                            align="start",
                            spacing="2",
                        ),
                        padding="1rem",
                        background="var(--gray-2)",
                        border_radius="var(--radius-2)",
                        width="100%",
                    ),
                    rx.flex(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                            on_click=State.close_delete_dialog,
                        ),
                        rx.button(
                            "Continue",
                            color_scheme="red",
                            on_click=State.confirm_delete,
                        ),
                        spacing="3",
                        margin_top="16px",
                        justify="end",
                    ),
                    spacing="3",
                    width="100%",
                ),
                # Step 2: Confirmation
                rx.vstack(
                    rx.dialog.title(
                        rx.hstack(
                            rx.icon("triangle_alert", color="red", size=24),
                            "Confirm Deletion",
                            spacing="2",
                        )
                    ),
                    rx.callout(
                        rx.cond(
                            State.delete_remote_files,
                            "This will permanently delete the platform configuration AND all VOLTTRON files on the remote system. This cannot be undone!",
                            "This will permanently delete the platform configuration. This cannot be undone!",
                        ),
                        icon="triangle_alert",
                        color="red",
                    ),
                    rx.cond(
                        State.deleting_platform,
                        rx.hstack(
                            rx.spinner(size="2"),
                            rx.text("Deleting platform..."),
                            spacing="2",
                            padding="1rem",
                        ),
                        rx.flex(
                            rx.button(
                                "Back",
                                variant="soft",
                                color_scheme="gray",
                                on_click=State.back_to_delete_options,
                            ),
                            rx.button(
                                rx.cond(
                                    State.delete_remote_files,
                                    "Delete Platform & Remote Files",
                                    "Delete Platform",
                                ),
                                color_scheme="red",
                                on_click=State.handle_delete_platform,
                            ),
                            spacing="3",
                            margin_top="16px",
                            justify="end",
                        ),
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            max_width="450px",
        ),
        open=State.show_delete_dialog,
    )
