from volttron_installer.modules.attempt_to_update_control import attempt_to_update_control
from flet import colors, Container

def show_selected_tile(e, tile_container: Container) -> None:
    """Update the styling of the selected tile"""
    selected_tile_key = e.control.key
    for container in tile_container.controls:
        if container.key == selected_tile_key:
            container.bgcolor = "lightblue"  # Apply selected styling
        else:
            if isinstance(container, Container):
                container.bgcolor = colors.with_opacity(0.5, colors.BLUE_GREY_300)  # Reset non-selected tiles
        container.update()
