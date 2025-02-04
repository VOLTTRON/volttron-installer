import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.header.header import header
from ..components.tabs.state import PlatformState
from ..components.tabs import platform_config, agent_config

@rx.page(route="/platform/[uid]")
def platform_page() -> rx.Component:
    
    return app_layout(
        header(
            rx.text(f"Platform: {PlatformState.current_uid}"),
        ),
        rx.fragment(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Platform Config", value="tab_1"),
                    rx.tabs.trigger("Agent Config", value="tab_2"),
                ),
                rx.tabs.content(
                    # Access platform data using the UID
                    platform_config.platform_config_tab(PlatformState.current_uid),
                    value="tab_1"
                ),
                rx.tabs.content(
                    # Access platform data using the UID  
                    agent_config.agent_config_tab(PlatformState.current_uid),
                    value="tab_2"
                ),
                default_value="tab_1"
            )
        )
    )