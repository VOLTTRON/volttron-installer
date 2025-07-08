import reflex as rx
from ..model_views import AgentModelView

INDEX = "/"

# TODO get some dynamic routing in 
class NavigationState(rx.State):
    platform_routes: list[str] = []
    
    # Platform route management
    @rx.event
    async def add_platform_route(self, uid: str):
        if uid not in self.platform_routes:
            self.platform_routes.append(uid)

    @rx.event
    async def remove_platform_route(self, uid: str):
        if uid in self.platform_routes:
            self.platform_routes.remove(uid)

    # Basic navigation
    @rx.event
    def route_to_index(self):
        return rx.redirect("/", is_external=False)

    @rx.event
    def route_to_platform(self, uid: str):
        return rx.redirect(f"/platform/{uid}", is_external=False)

    @rx.event
    def route_to_bacnet_scan(self):
        return rx.redirect("/bacnet_scan", is_external=False)

    # Agent configuration navigation
    @rx.event
    async def route_to_agent_config(self, platform_uid: str, agent_uid: str, agent: AgentModelView):
        """Route to agent config page and initialize its state."""
        # from ..pages.agent_config_page import AgentConfigState

        # agent_config_state = await self.get_state(AgentConfigState)
        # await agent_config_state.hydrate_working_agent()
        return rx.redirect(f"/platform/{platform_uid}/agent/{agent_uid}")

    @rx.event 
    def route_back_to_platform(self, platform_uid: str):
        """Route back to platform page from agent config."""
        return rx.redirect(f"/platform/{platform_uid}")