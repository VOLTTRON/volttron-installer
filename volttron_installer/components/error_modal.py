from flet import AlertDialog, Container, Text, Column
from volttron_installer.modules.styles import modal_styles2

def error_modal() -> AlertDialog:
    return AlertDialog(
            bgcolor="#00000000",
            modal = False,
            content=Container(
                **modal_styles2(),
                height=150,
                content=Column(
                    [
                        Text("ERROR", size=22, color="red",),
                        Text("Improper JSON or YAML was entered,"),
                        Text("Your custom configuration has not saved")
                    ]
                )
            )
        )