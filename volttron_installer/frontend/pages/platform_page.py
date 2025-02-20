import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.buttons import icon_button_wrapper
from ..components.header.header import header
from ..components.tabs.state import PlatformState
from ..components.tabs import platform_config, agent_config
from ..navigation.state import NavigationState
from ..components.form_components import form_entry
from ...backend.models import HostEntry, PlatformDefinition

# storing stuff here just for now, will move to a better place later

import string, random, json
class Instance(rx.Base):
    host: HostEntry
    platform: PlatformDefinition
    advanced_expanded: bool = False


class State(rx.State):
    platforms: dict[str, Instance] = {}

    @rx.var(cache=True)
    def current_uid(self) -> str:
        return self.router.page.params.get("uid", "")

    @rx.event
    async def generate_new_platform(self):
        new_uid = self.generate_unique_uid()
        new_host = HostEntry(id="", ansible_user="", ansible_host="")
        new_platform = PlatformDefinition()
        self.platforms[new_uid] = Instance(host=new_host, platform=new_platform)

        nav_state: NavigationState = await self.get_state(NavigationState)
        await nav_state.add_platform_route(new_uid)

    @rx.event
    def toggle_advanced(self):
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.advanced_expanded = not working_platform.advanced_expanded

    def generate_unique_uid(self, length=7) -> str:
        characters = string.ascii_letters + string.digits
        while True:
            new_uid = ''.join(random.choice(characters) for _ in range(length))
            if new_uid not in self.platforms:
                return new_uid


@rx.page(route="/platform/[uid]")
def platform_page() -> rx.Component:

    working_platform: Instance = State.platforms[State.current_uid]
    return app_layout(
        header(
            icon_button_wrapper.icon_button_wrapper(
                tool_tip_content="Go back to overview",
                icon_key="arrow-left",
                on_click=lambda: NavigationState.route_to_index()
            ),
            rx.text(f"Platform: {PlatformState.current_uid}", size="5"),
        ),
        rx.box(
            rx.accordion.root(
                rx.accordion.item(
                    header="Connection",
                    content=rx.box(
                        rx.box(
                            form_entry.form_entry(
                                "Host",
                                rx.input(
                                    size="3",
                                    required=True,
                                )
                            ),
                            form_entry.form_entry(
                                "Username",
                                rx.input(
                                    size="3",
                                    required=True,
                                )
                            ),
                            form_entry.form_entry(
                                "Port SSH",
                                rx.input(
                                    size="3",
                                    required=True,
                                )
                            ),
                            rx.box(
                                rx.hstack(
                                    rx.text("Toggle Advanced"),
                                    rx.cond(
                                        working_platform.advanced_expanded,
                                        rx.icon("chevron-up"),
                                        rx.icon("chevron-down")
                                    )
                                ),
                                class_name="toggle_advanced_button",
                                on_click=lambda: State.toggle_advanced(State.current_uid)
                            ),
                            rx.cond(
                                working_platform.advanced_expanded,
                                rx.fragment(
                                    form_entry.form_entry(
                                        "HTTPS Proxy",
                                        rx.input(
                                            size="3",
                                            required=True,
                                        )
                                    ),
                                    form_entry.form_entry(
                                        "VOLTTRON Home",
                                        rx.input(
                                            size="3",
                                            required=True,
                                        )
                                    ),
                                    form_entry.form_entry(
                                        "SSH config stuff",
                                        rx.input(
                                            size="3",
                                            required=True,
                                        )
                                    ),
                                )
                            ),
                            class_name="platform_content_view"
                        ),
                        class_name="platform_content_container"
                    )
                    # rx.accordion.content(
                    #     rx.text("This is connection")
                    # )
                ),
                rx.accordion.item(
                    header="Platform Configuration",
                    content=rx.box(
                        rx.box(
                            form_entry.form_entry(
                                "Vip Identity",
                                rx.input(
                                    size="3",
                                    required=True,
                                )
                            ),
                            rx.button("Start a Web", variant="surface", size="2"),
                            rx.button("install x agents", variant="surface", size="2"),
                            rx.button("configuration of agents", variant="surface", size="2"),
                            rx.button("config Store editor", variant="surface", size="2"),
                            # form_entry.form_entry(
                                
                            # ),
                            # form_entry.form_entry(
                                
                            # ),
                            # form_entry.form_entry(
                                
                            # ),
                            
                            class_name="platform_content_view"
                        ),
                        class_name="platform_content_container"
                    )
                    # rx.accordion.trigger("Instance Configuration"),
                    # rx.accordion.content(
                    #     rx.text("This is Instance Configuration")
                    #     # agent_config.agent_config_tab(PlatformState.current_uid)
                    # )
                ),
                collapsible=True,
                variant="outline"
            ),
            rx.box(
                rx.button("Save", size="4", variant="surface", color_scheme="green"),
                rx.button("Deploy", size="4", variant="surface", color_scheme="blue"),
                rx.button("Cancel", size="4", variant="surface", color_scheme="red"),
                class_name="platform_view_button_row"
            ),
            class_name="platform_view_container"
        ),
        # rx.fragment(
        #     rx.tabs.root(
        #         rx.tabs.list(
        #             rx.tabs.trigger("Platform Config", value="tab_1"),
        #             rx.tabs.trigger("Agent Config", value="tab_2"),
        #         ),
        #         rx.tabs.content(
        #             # Access platform data using the UID
        #             platform_config.platform_config_tab(PlatformState.current_uid),
        #             value="tab_1"
        #         ),
        #         rx.tabs.content(
        #             # Access platform data using the UID  
        #             agent_config.agent_config_tab(PlatformState.current_uid),
        #             value="tab_2"
        #         ),
        #         default_value="tab_1"
        #     )
        # )
    )