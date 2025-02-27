import reflex as rx

INDEX = "/"

# TODO get some dynamic routing in 
class NavigationState(rx.State):
    platform_routes: list[str] = []

    @rx.event
    async def add_platform_route(self, uid: str):
        if uid not in self.platform_routes:
            print(f"I also added bro {uid}")
            self.platform_routes.append(uid)

    @rx.event
    async def remove_platform_route(self, uid: str):
        if uid in self.platform_routes:
            self.platform_routes.remove(uid)

    @rx.event
    def route_to_platform(self, uid: str):
        return rx.redirect(f"/platform/{uid}", is_external=False)
    
    @rx.event
    def route_to_index(self):
        return rx.redirect(INDEX, is_external=False)