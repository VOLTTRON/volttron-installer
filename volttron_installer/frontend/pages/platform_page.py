import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.buttons import icon_button_wrapper
from ..components.header.header import header
from ..components.tabs.state import PlatformState
from ..components.tabs import platform_config, agent_config
from ..navigation.state import NavigationState

@rx.page(route="/platform/[uid]")
def platform_page() -> rx.Component:
    
    return app_layout(
        header(
            icon_button_wrapper.icon_button_wrapper(
                tool_tip_content="Go back to overview",
                icon_key="arrow-left",
                on_click=lambda: NavigationState.route_to_index()
            ),
            rx.text(f"Platform: {PlatformState.current_uid}", size="5"),
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