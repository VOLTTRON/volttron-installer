from flet import *


def gradial_background() -> Container:
    """
    Returns a default background style for consistency
    """
    return Container(
        expand=True,
        content=Stack(
            [            
                Container(
                    gradient=RadialGradient(
                        colors=["#8aed07","#08afa8","#005d55","#01411f","#01213a"],
                        # colors=[colors.PURPLE, colors.BLACK],
                        radius=1.4,
                        center=Alignment(0.8, 0.8)
                    )
                ),
                Container(
                    blur=Blur(300,300,BlurTileMode.REPEATED),
                )
            ]
        )
    )