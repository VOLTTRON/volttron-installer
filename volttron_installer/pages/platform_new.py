import reflex as rx
from .platform_page import State as PlatformPageState

class State(rx.State):
    @rx.event
    def create_redirect(self):
        yield PlatformPageState.generate_new_platform

@rx.page(route="/platform/new", on_load=State.create_redirect)
def new_platform_page() -> rx.Component:
    return rx.container()