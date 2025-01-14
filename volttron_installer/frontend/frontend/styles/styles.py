import reflex as rx
styles: dict = {
    ".upload_button" : {
        "border-radius" : ".5rem",
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
    
    "upload_svg_container" : {
        "width" : ".5rem",
        "height" : ".5rem"
    },
    rx.button : {
        "cursor": "pointer"
    }
}