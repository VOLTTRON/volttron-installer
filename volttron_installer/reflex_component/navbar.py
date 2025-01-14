import reflex as rx

def navbar() -> rx.Component:
    return rx.container(
        rx.link("Home", "/"),
        rx.link("Platform", "/platform"),
        rx.link("Ansible", "/ansible"),
        rx.link("Tasks", "/tasks"),
        rx.link("Settings", "/settings"),
        rx.link("About", "/about"),
        rx.link("Logout", "/logout"),
        style={"padding": "10px", "background-color": "#f1f1f1"},
    )
