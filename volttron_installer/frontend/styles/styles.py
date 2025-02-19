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

    rx.button : {
        "cursor": "pointer",
        "transition": HOVER_TRANSITION
    }
}