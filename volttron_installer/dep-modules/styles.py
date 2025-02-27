from flet import *

def modal_styles()-> dict:
    return {
        "border_radius" : 15,
        "bgcolor" : colors.with_opacity(0.93, "#ffffff"),
        "padding" : 10,
        "blur" : Blur(10,10,BlurTileMode.REPEATED),
        "shadow" : BoxShadow(
                    spread_radius=1,
                    blur_radius=30,
                    color=colors.BLUE_GREY_300,
                    offset=Offset(0,0),
                    blur_style=ShadowBlurStyle.OUTER,
                    ),
    }

def modal_styles2()-> dict:
    return {
        "border_radius" : 15,
        "bgcolor" : "#20f4f4f4",
        # "bgcolor" : colors.with_opacity(0.83, colors.BLUE_GREY_200),
        "padding" : 10,
        "blur" : Blur(10,10,BlurTileMode.REPEATED),
        #  "shadow" : BoxShadow(
        #              spread_radius=0,
        #              blur_radius=0,
        #              color="white",
        #              offset=Offset(0,0),
        #              blur_style=ShadowBlurStyle.OUTER,
        #              ),
    }
def data_table_styles() -> dict:
    return {
        "expand" : True,
        "border_radius" : 8,
        "border" : border.all(2, "#ebebeb"),
        "horizontal_lines" : border.BorderSide(1, "#ebebeb"),
        "vertical_lines" : border.BorderSide(1, "#ebebeb")
    }

def progress_styles()-> dict:
    return {
        "default_color" : "#D2D3D3",
        "completed_color" : "blue",
        "finalized_color": "green",
        "check_color" : "white"
    }

def pulsing_changes_circle() -> dict:
    return {
        "border_radius" : 50,
        "gradient" : RadialGradient(
                        center=Alignment(0.0, 0.0),
                        colors=[colors.with_opacity(0.6, "white"), colors.with_opacity(0.6, "orange")]
                    )
    }