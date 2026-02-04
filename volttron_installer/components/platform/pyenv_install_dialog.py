import reflex as rx
from ...state import PlatformPageState as State

def pyenv_install_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Install Python 3.10 via pyenv"),
                rx.dialog.description(
                    "Install Python 3.10 on the remote host using pyenv and create the VOLTTRON venv.",
                    size="1",
                ),
                rx.text(
                    "Python 3.10 is required but not found on the remote host. "
                    "Would you like to install it using pyenv?",
                    size="2",
                    color="gray",
                ),
                rx.cond(
                    State.pyenv_error != "",
                    rx.callout(
                        State.pyenv_error,
                        icon="triangle_alert",
                        color="red",
                        size="1",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    State.pyenv_installing,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("Installing Python 3.10 via pyenv... This may take several minutes.", size="2"),
                        spacing="2",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.button(
                        "Install with pyenv",
                        on_click=State.handle_install_pyenv,
                        disabled=State.pyenv_installing,
                        loading=State.pyenv_installing,
                    ),
                    rx.button(
                        "Cancel",
                        variant="soft",
                        on_click=State.close_pyenv_dialog,
                        disabled=State.pyenv_installing,
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            max_width="600px",
        ),
        open=State.show_pyenv_dialog,
    )
