import reflex as rx

root_styles: dict = {
    "--btn-primary" : "grey",
    "--btn-active" : "blue",
    "--hover-primary" : "#2A2A2C",
    "--hover-active" : "darkblue"
}

HOVER_TRANSITION = "color 0.3s ease, background-color 0.3s ease"

CUSTOM_BUTTON_PADDING = ".25rem .75rem"

COMMON_BORDER_RADIUS = ".5rem"

COMMON_BUTTON_STRUCTURE = {
        "cursor" : "pointer",
        "border-radius" : COMMON_BORDER_RADIUS,
        "padding" : CUSTOM_BUTTON_PADDING,
        "transition": HOVER_TRANSITION,
        "user-select" : "none",
}

styles: dict = {
    ":root": {
        "--btn-primary" : "grey",
        "--btn-active" : "blue",
        "--hover-primary" : "darkgrey",
        "--hover-active" : "darkblue"
    },
    ".form_selection_button" : {
        "display" : "flex",
        "min-width" : "7rem",
        "min-height" : "2rem",
        "border-radius" : COMMON_BORDER_RADIUS,
        "cursor" : "pointer",
        "padding" : ".25rem",
        "user-select" : "none",
        "justify-content" : "start",
        "align-items" : "start",
        "transition" : HOVER_TRANSITION,
    },
    ".upload_button" : {
        "border-radius" : COMMON_BORDER_RADIUS,
        "color" : "white",
        "font-size" : "12px",
        "font-weight" : "bold",
        "user-select" : "none",
        "display" : "flex",
        "cursor" : "pointer",
        "flex-direction" : "row",
        "padding" : CUSTOM_BUTTON_PADDING
    },

    ".platform_tile" : {
        "border-radius" : COMMON_BORDER_RADIUS,
        "width" : "9rem",
        "height" : "9rem",
        "padding" : CUSTOM_BUTTON_PADDING,
        "background-color" : "blue",
        "cursor" : "pointer",
        "user-select" : "none"
    },
    
    "upload_svg_container" : {
        "width" : ".5rem",
        "height" : ".5rem"
    },
    ".icon_button": {
        "cursor" : "pointer",
        "border-radius" : COMMON_BORDER_RADIUS,
        "padding" : ".25rem",
        "transition": HOVER_TRANSITION
    },
    ".icon_button:hover" : {
        "background-color" : "#2A2A2C"
    },

    ".csv_data_cell" : {
        "cursor" : "pointer",
        "transition": HOVER_TRANSITION,
        "user_select": "none",
        "min-width" : "6rem"
    },
    ".csv_data_cell:hover" : {
        # "background-color" : "#2A2A2C",
        "background-color" : root_styles["--hover-primary"]
    },
    ".text_editor": {
        "font-family": "Consolas",
    },

    ".platform_view_button_row" : {
        "display" : "flex",
        "flex-direction" : "row",
        "justify-content" : "center",
        "column-gap" : "2rem",
        "padding" : "1rem"
        # spacing whatever
    },

    ".platform_view_container": {
        "padding-left" : "clamp(1rem, 10vw, 10rem)",
        "padding-right" : "clamp(1rem, 10vw, 10rem)",
    },

    ".platform_content_container": {
        "width" : "100%",
        "display":"flex",
        "flex-direction" : "column",
        "min-height": "20rem",
        # "background-color" : "pink",
    },

    ".platform_content_view": {
        "display" : "flex",
        "flex-direction" : "column",
        "padding" : "1rem",
        "row-gap" : "2rem",
        # "background-color" : "white",
        "align-items" : "center",
        "color": "white"
    },

    ".toggle_advanced_button": {
        "cursor" : "pointer",
        "border-radius" : COMMON_BORDER_RADIUS,
        "padding" : CUSTOM_BUTTON_PADDING,
        "transition": HOVER_TRANSITION,
        "user-select" : "none",
        "background-color" : "#2A2A2C"
    },

    ".toggle_advanced_button:hover": {
        "background-color" : "#333335"
    },

    ".platform_control_buttons": {
        # *COMMON_BUTTON_STRUCTURE()
    },

    ".agent_config_views": {
        "flex": "1",  # Ensure the container takes up equal space
        "border": "1px solid white",
        "border-radius": ".5rem",
        "padding": "1rem",
        "display": "flex",  # Ensure it works as a flex container
        # "flex-direction": "column"  # Handle children as columns
    },

    ".agent_config_view_content": {
        "display": "flex",
        "flex-direction": "column",
        "row-gap": "1rem",
        "align-items": "center",
        "flex": "1"  # Take up all the available space within the column
    },

    ".agent_config_container": {
        "width": "60rem",
        "height": "40rem",
        # "border": "1px solid white",
        "display" : "flex",
        "flex-direction" : "row",
        "column-gap" : "2rem"
    },

    ".agent_config_tile" : {
        "display" : "flex",
        "min-width" : "7rem",
        "min-height" : "2rem",
        "border-radius" : COMMON_BORDER_RADIUS,
        "cursor" : "pointer",
        "padding" : ".25rem",
        "user-select" : "none",
        "justify-content" : "start",
        "align-items" : "start",
        "transition" : HOVER_TRANSITION,
        "background-color": "#2A2A2C"
    },

    ".agent_config_tile:hover" : {
        "background-color" : "#333335"
    },

    ".agent_config_modal_container": {
        "padding-left" : "3rem",
        "padding-right" : "3rem",
    },

    ".agent_config_modal" :{
        "display": "flex",
        "flex-direction": "column",
        "align-items": "center",
        "row-gap": "5rem",
        "row" : "3rem",
        "flex": "1"
    },

    ".agent_config_entry_section": {
        "display": "flex",
        "flex-direction": "column",
        "row-gap": "1rem",
        "align-items": "center",
        "flex": "1"  # Take up all the available space within the column
    },

    rx.button : {
        "cursor": "pointer",
        "transition": HOVER_TRANSITION
    }
}