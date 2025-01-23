import reflex as rx

root_styles: dict = {
    "--btn-primary" : "grey",
    "--btn-active" : "blue",
    "--hover-primary" : "darkgrey",
    "--hover-active" : "darkblue"
}
HOVER_TRANSITION = "color 0.3s ease, background-color 0.3s ease"


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
        "border-radius" : ".5rem",
        "cursor" : "pointer",
        "padding" : ".25rem",
        "user-select" : "none",
        "justify-content" : "start",
        "align-items" : "start",
        "transition" : HOVER_TRANSITION,
    },
    ".upload_button" : {
        "border-radius" : ".25rem",
        "color" : "orange",
        "font-size" : "12px",
        "user-select" : "none",
        "display" : "flex",
        "cursor" : "pointer",
        "flex-direction" : "row",
        "border" : "2px solid blue",
        "_hover": {
            "color": "black",
            "background_color": "white"
        }
    },

    ".platform_tile" : {
        "border-radius" : ".5rem",
        "width" : "9rem",
        "height" : "9rem",
        "padding" : ".25rem .75rem",
        "background-color" : "blue",
        "cursor" : "pointer",
        "user-select" : "none"
    },
    
    "upload_svg_container" : {
        "width" : ".5rem",
        "height" : ".5rem"
    },
    rx.button : {
        "cursor": "pointer"
    }
}