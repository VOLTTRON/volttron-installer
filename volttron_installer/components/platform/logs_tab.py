import reflex as rx
from ...state import PlatformPageState as State

def logs_tab_content() -> rx.Component:
    """Tab content for viewing VOLTTRON logs"""
    return rx.vstack(
        rx.hstack(
            rx.heading("VOLTTRON Logs", size="5"),
            rx.hstack(
                rx.button(
                    rx.icon("minus", size=18),
                    "Smaller",
                    on_click=State.decrease_log_font_size,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("plus", size=18),
                    "Larger",
                    on_click=State.increase_log_font_size,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("wrap-text", size=18),
                    "Wrap",
                    on_click=State.toggle_log_wrap,
                    size="2",
                    variant=rx.cond(State.log_wrap, "solid", "soft"),
                ),
                rx.cond(
                    State.tailing,
                    rx.button(
                        rx.icon("square", size=18),
                        "Stop Tail",
                        on_click=State.stop_tailing,
                        size="2",
                        variant="solid",
                        color_scheme="red",
                    ),
                    rx.button(
                        rx.icon("play", size=18),
                        "Live Tail",
                        on_click=State.start_tailing,
                        size="2",
                        variant="soft",
                        color_scheme="green",
                    ),
                ),
                rx.button(
                    rx.icon("refresh-cw", size=18),
                    "Refresh Logs",
                    on_click=State.fetch_platform_logs(100),
                    loading=State.logs_loading,
                    disabled=State.tailing,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("trash-2", size=18),
                    "Delete Log",
                    on_click=State.delete_platform_logs,
                    loading=State.logs_loading,
                    disabled=State.tailing,
                    size="2",
                    variant="soft",
                    color_scheme="red",
                ),
                spacing="2",
            ),
            justify="between",
            width="100%",
            padding_bottom="1rem",
        ),
        rx.card(
            rx.scroll_area(
                rx.el.pre(
                    rx.foreach(
                        State.parsed_log_lines,
                        lambda log_line: rx.el.div(
                            log_line["text"],
                            style={
                                "color": rx.match(
                                    log_line["level"],
                                    ("debug", "var(--gray-9)"),
                                    ("info", "var(--blue-11)"),
                                    ("warning", "var(--orange-11)"),
                                    ("error", "var(--red-11)"),
                                    ("critical", "var(--red-12)"),
                                    "var(--gray-12)",
                                ),
                                "fontWeight": rx.cond(
                                    log_line["level"] == "critical",
                                    "bold",
                                    "normal",
                                ),
                            },
                        ),
                    ),
                    style={
                        "fontSize": State.log_font_size.to(str) + "px",
                        "whiteSpace": rx.cond(State.log_wrap, "pre-wrap", "pre"),
                        "wordBreak": rx.cond(State.log_wrap, "break-word", "normal"),
                        "overflowWrap": rx.cond(State.log_wrap, "break-word", "normal"),
                        "fontFamily": "monospace",
                        "margin": "0",
                        "padding": "1em",
                        "backgroundColor": "var(--gray-2)",
                        "borderRadius": "var(--radius-2)",
                    },
                ),
                type="auto",
                scrollbars="both",
                style={"height": "calc(100vh - 250px)", "width": "100%"},
            ),
            width="100%",
        ),
        spacing="3",
        width="100%",
    )
