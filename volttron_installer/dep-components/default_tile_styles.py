from flet import Container, IconButton, colors, padding, Row, icons, MainAxisAlignment, Text

def build_default_tile(content: str) -> Container:
    """
    Creates a styled container (tile) with the provided content and a delete button.

    Args:
        content: Typically a string but can be any type that can be converted to a string
        for display.

    Returns:
        A Container object styled and populated with the provided content and a delete button.
    """
    # Create a delete button with a placeholder for the on_click event
    delete_button = IconButton(
        icon=icons.DELETE,
        # The on_click event will be re-assigned later
    )

    # Construct the Container (tile) with various styles and controls
    return Container(
        border_radius=15,  # Set rounded corners with a radius of 15
        padding=padding.only(left=7, right=7, top=5, bottom=5),  # Add padding around the container
        bgcolor=colors.with_opacity(0.5, colors.BLUE_GREY_300),  # Set the background color with some opacity
        
        # Content of the container: a row containing text and a delete button
        content=Row(
            wrap=True,  # Allow wrapping of controls within the row
            controls=[
                Text(value=content),  # Display the provided content as a Text control
                delete_button  # Add the delete button
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN  # Space controls evenly within the row
        )
    )


def build_tile_with_agent_tile(content: Container) -> Container:
    return