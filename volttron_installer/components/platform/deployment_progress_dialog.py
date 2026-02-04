import reflex as rx
from ...state import PlatformPageState as State

def deployment_progress_dialog() -> rx.Component:
    """Dialog showing deployment progress with task name and logs"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Deploying Platform"),
                rx.dialog.description(
                    rx.text(State.current_task, size="3", weight="bold")
                ),
                rx.progress(value=State.deployment_progress, max=100, width="100%"),
                rx.text(
                    rx.cond(
                        State.deployment_progress > 0,
                        f"{State.deployment_progress}% complete",
                        "Starting...",
                    ),
                    size="1",
                    color="gray",
                ),
                rx.cond(
                    State.show_pyenv_prompt,
                    rx.callout(
                        rx.vstack(
                            rx.text(
                                rx.cond(
                                    State.pyenv_error != "",
                                    State.pyenv_error,
                                    "Python 3.10 is required but not found.",
                                ),
                                weight="bold",
                            ),
                            rx.text(
                                "After installing Python 3.10, add the path to the platform's Advanced Settings (Custom Python Path).",
                                size="1",
                            ),
                            spacing="1",
                            align="start",
                        ),
                        icon="triangle_alert",
                        color="yellow",
                        size="2",
                    ),
                    rx.fragment(),
                ),
                rx.box(
                    rx.vstack(
                        rx.foreach(
                            State.deployment_steps,
                            lambda step: rx.hstack(
                                rx.cond(
                                    step["status"] == "running",
                                    rx.spinner(size="1"),
                                    rx.cond(
                                        step["status"] == "success",
                                        rx.icon("check", size=16, color="green"),
                                        rx.icon("x", size=16, color="red"),
                                    ),
                                ),
                                rx.text(step["name"], size="2"),
                                spacing="2",
                                align="center",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    width="100%",
                    padding="0.5rem",
                    border="1px solid var(--gray-4)",
                    border_radius="8px",
                    background_color="var(--gray-1)",
                ),
                # Log output area
                rx.box(
                    rx.vstack(
                        rx.foreach(
                            State.deployment_logs,
                            lambda log: rx.text(log, size="1", font_family="monospace")
                        ),
                        width="100%",
                        spacing="1",
                    ),
                    width="100%",
                    height=rx.cond(State.show_pyenv_prompt, "220px", "300px"),
                    overflow_y="auto",
                    padding="1rem",
                    border="1px solid var(--gray-6)",
                    border_radius="8px",
                    background_color="var(--gray-2)",
                ),
                # Progress indicator
                rx.cond(
                    State.is_deploying,
                    rx.hstack(
                        rx.spinner(size="3"),
                        rx.text("Deploying...", size="2"),
                        spacing="3",
                        align="center",
                    ),
                    rx.cond(
                        State.deployment_status == "success",
                        rx.hstack(
                            rx.icon("check", size=24, color="green"),
                            rx.text("Deployment completed", size="2", color="green"),
                            spacing="3",
                            align="center",
                        ),
                        rx.hstack(
                            rx.icon("x", size=24, color="red"),
                            rx.text("Deployment failed", size="2", color="red"),
                            spacing="3",
                            align="center",
                        ),
                    ),
                ),
                # Action buttons
                rx.hstack(
                    rx.cond(
                        State.show_pyenv_prompt,
                        rx.button(
                            "Install Python 3.10 with pyenv",
                            on_click=State.handle_install_pyenv,
                            disabled=State.pyenv_installing,
                            loading=State.pyenv_installing,
                        ),
                        rx.fragment(),
                    ),
                    rx.dialog.close(
                        rx.button(
                            "Close",
                            on_click=State.close_deployment_dialog,
                            disabled=State.is_deploying,
                        )
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px",
        ),
        open=State.show_deployment_dialog,
    )
