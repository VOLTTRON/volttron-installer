"""Live vctl config store section."""

import reflex as rx
from ...state import PlatformPageState as State


def _tree_row(row: dict) -> rx.Component:
    """Render one row of the config store tree — either an agent header or a key entry."""
    return rx.cond(
        row["type"] == "agent",
        # ── Agent header row ──────────────────────────────────────────────
        rx.hstack(
            rx.cond(
                row["expanded"],
                rx.icon("chevron-down", size=15, color="gray"),
                rx.icon("chevron-right", size=15, color="gray"),
            ),
            rx.icon("layers", size=15, color="#60a5fa"),
            rx.text(
                row["agent"],
                size="2",
                weight="medium",
                font_family="monospace",
                flex="1",
            ),
            rx.cond(
                row["loading"],
                rx.spinner(size="1"),
                rx.fragment(),
            ),
            on_click=State.toggle_agent_tree(row["agent"]),
            style={"cursor": "pointer"},
            spacing="2",
            align="center",
            padding_y="5px",
            padding_x="4px",
            border_radius="4px",
            _hover={"background": "var(--gray-3)"},
            width="100%",
        ),
        # ── Config key row ────────────────────────────────────────────────
        rx.hstack(
            rx.hstack(
                rx.icon("file-text", size=14, color="gray"),
                rx.text(
                    row["key"],
                    size="2",
                    font_family="monospace",
                    flex="1",
                    no_of_lines=1,
                ),
                spacing="2",
                align="center",
                flex="1",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=14),
                    rx.text(
                        "Edit",
                        class_name="cfg-action-label",
                        style={"@media (max-width: 1280px)": {"display": "none"}},
                    ),
                    size="1",
                    variant="soft",
                    color_scheme="gray",
                    loading=State.live_key_loading & (State.live_editing_key == row["key"]),
                    on_click=State.open_edit_live_config_key(row["agent"], row["key"]),
                    min_width="52px",
                    title="Edit key",
                ),
                rx.button(
                    rx.icon("trash-2", size=14),
                    rx.text(
                        "Delete",
                        class_name="cfg-action-label",
                        style={"@media (max-width: 1280px)": {"display": "none"}},
                    ),
                    size="1",
                    variant="soft",
                    color_scheme="red",
                    on_click=State.open_delete_live_config_dialog(row["agent"], row["key"]),
                    min_width="52px",
                    title="Delete key",
                ),
                spacing="2",
                align="center",
                flex_shrink="0",
            ),
            spacing="2",
            align="center",
            padding_left="2rem",
            padding_y="8px",
            padding_right="0.5rem",
            border_radius="6px",
            _hover={"background": "var(--gray-2)"},
            width="100%",
        ),
    )


def platform_driver_config_section() -> rx.Component:
    """Section showing live vctl config store as a dynamic, flicker-free tree."""
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("Live Config Store", size="4", weight="bold"),
                rx.text(
                    "Driver config keys currently loaded in the running platform (edit or delete from here).",
                    size="1",
                    color="gray",
                ),
                rx.text(
                    "Tip: On smaller screens, action labels collapse to icons to keep rows readable.",
                    size="1",
                    color="gray",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.cond(
                State.vctl_agents_loading,
                rx.hstack(
                    rx.spinner(size="1"),
                    rx.text("Refreshing…", size="1", color="gray"),
                    spacing="1",
                    align="center",
                ),
                rx.button(
                    rx.icon("refresh-cw", size=13),
                    "Refresh",
                    on_click=State.fetch_vctl_config_list,
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                ),
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        rx.cond(
            State.vctl_config_agents.length() > 0,
            rx.box(
                rx.foreach(State.config_tree_rows, _tree_row),
                width="100%",
                min_height="320px",
                max_height="420px",
                overflow_y="auto",
                border="1px solid var(--gray-5)",
                border_radius="10px",
                padding="0.5rem",
                background="var(--gray-1)",
            ),
            rx.cond(
                State.vctl_agents_loading,
                rx.fragment(),
                rx.callout(
                    rx.text(
                        "No agents found in config store yet. Click Refresh to scan active config entries.",
                        size="2",
                    ),
                    icon="search",
                    color_scheme="gray",
                ),
            ),
        ),
        spacing="2",
        width="100%",
    )