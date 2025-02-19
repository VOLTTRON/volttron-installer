from flet import *

class GeneralNotifier():
    """Generalized SnackBar to serve as confirmation for
    a variety of user functions."""
    def __init__(self, page: Page):
        self.page = page

        # Added for consistency.
        self.preset_messages = {
            1: "Changes Saved!",
            2: "Changes Reverted!"
        }
        
    def display_snack_bar(self, message: str | int) -> None:
        """Displays a snackbar on the top of the page with a custom or preset message
        
            - 1 : `Changes Saved!`
            - 2 : `Changes Reverted!`
            """


        if isinstance(message, int) and message in self.preset_messages:
            display_message = self.preset_messages[message]
        else:
            display_message = message
        
        self.page.snack_bar = SnackBar(
            content = Row(
                controls=[
                    Text(f"{display_message}"),
                ],
                alignment=MainAxisAlignment.CENTER
            ),
            behavior=SnackBarBehavior.FLOATING,
            dismiss_direction=DismissDirection.UP,
            margin=margin.only(bottom=self.page.height-100, right=(self.page.width * 0.4), left=(self.page.width * 0.4)),
        )
        self.page.snack_bar.open = True
        self.page.update()