import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.buttons import icon_button_wrapper
from ..components.header.header import header
from ..navigation.state import NavigationState
from ..components.form_components import form_entry
from ...backend.models import HostEntry, PlatformDefinition

# storing stuff here just for now, will move to a better place later

import string, random, json

class Instance(rx.Base):
    host: HostEntry
    platform: PlatformDefinition
    safe_host: dict = {}

    valid: bool = False
    uncaught: bool = False   
    # deployed: bool = False

    advanced_expanded: bool = False
    agent_config_expanded: bool = False
    web_checked: bool = False
    
    def is_uncaught(self) -> bool:
        current_host = self.host.to_dict()
        return current_host != self.safe_host

    def does_host_have_errors(self) -> bool:
        host_dict = self.host.to_dict()
        
        # Check if any of the required fields are missing or empty
        has_errors = not all([host_dict.get("id"), host_dict.get("ansible_user"), host_dict.get("ansible_host")])
        
        if has_errors:
            print("Error: Missing host details", host_dict)

        print(f'am i tripping?: {has_errors}')

        # Return the boolean indicating if there are errors
        return has_errors


class State(rx.State):
    platforms: dict[str, Instance] = {}

    @rx.var(cache=True)
    def current_uid(self) -> str:
        return self.router.page.params.get("uid", "")

    @rx.event
    async def generate_new_platform(self):
        new_uid = self.generate_unique_uid()
        new_host = HostEntry(
            id="", 
            ansible_user="", 
            ansible_host=""
            )
        new_platform = PlatformDefinition()
        self.platforms[new_uid] = Instance(host=new_host, platform=new_platform, safe_host=new_host.to_dict())

        nav_state: NavigationState = await self.get_state(NavigationState)
        await nav_state.add_platform_route(new_uid)
        yield rx.toast.info("New platform created")

    @rx.event
    def update_detail(self, field: str, value):
        working_platform: Instance = self.platforms[self.current_uid]
        setattr(working_platform.host, field, value)
        self.handle_changes(working_platform)

    @rx.event
    def toggle_advanced(self):
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.advanced_expanded = not working_platform.advanced_expanded

    @rx.event
    def handle_web_toggle(self):
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.web_checked = not working_platform.web_checked

    @rx.event
    def toggle_agent_config_view(self):
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.agent_config_expanded = not working_platform.agent_config_expanded

    def handle_changes(self, working_platform: Instance):
        working_platform.valid = not working_platform.does_host_have_errors()
        working_platform.uncaught = working_platform.is_uncaught()

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
            rx.text(f"Platform: {State.current_uid}", size="5"),
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
                                    value=working_platform.host.id,
                                    on_change=lambda value: State.update_detail("id", value),  
                                    size="3",
                                ),
                                required_entry=True,
                            ),
                            form_entry.form_entry(
                                "Username",
                                rx.input(
                                    value=working_platform.host.ansible_user,
                                    on_change=lambda value: State.update_detail("ansible_user", value),
                                    size="3",
                                ),
                                required_entry=True,
                            ),
                            form_entry.form_entry(
                                "Port SSH",
                                rx.input(
                                    value=working_platform.host.ansible_port,
                                    on_change=lambda value: State.update_detail("ansible_port", value),
                                    size="3",
                                ),
                                required_entry=True,
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
                            form_entry.form_entry(
                                "Web",
                                rx.checkbox(
                                    checked=working_platform.web_checked,
                                    on_change=lambda: State.handle_web_toggle(),
                                    size="3",
                                )
                            ),
                            rx.cond(
                                working_platform.web_checked,
                                form_entry.form_entry(
                                    "Platform Name",
                                    rx.input(
                                        size="3",
                                        required=True,
                                    )
                                ),
                            ),
                            rx.box(
                                rx.hstack(
                                    rx.text("Agent Configuration"),
                                    rx.cond(
                                        working_platform.agent_config_expanded,
                                        rx.icon("chevron-up"),
                                        rx.icon("chevron-down")
                                    )
                                ),
                                class_name="toggle_advanced_button",
                                on_click=lambda: State.toggle_agent_config_view()
                            ),
                            rx.box(
                                rx.hstack(
                                    rx.vstack(),
                                    rx.vstack()
                                )
                            ),
                            width="100%",
                            height="20rem",
                            border="1px solid white",
                            class_name="platform_content_view"
                        ),
                        class_name="platform_content_container"
                    )
                ),
                collapsible=True,
                variant="outline"
            ),
            rx.box(
                rx.button(
                    "Save", 
                    size="4",
                    variant="surface", 
                    color_scheme="green"
                    ),
                rx.button(
                    "Deploy", 
                    size="4", 
                    variant="surface", 
                    color_scheme="blue"
                    ),
                rx.button(
                    "Cancel", 
                    size="4", 
                    variant="surface", 
                    color_scheme="red"
                    ),
                class_name="platform_view_button_row"
            ),
            class_name="platform_view_container"
        ),
    )