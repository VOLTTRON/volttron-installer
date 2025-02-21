from volttron_installer.modules.styles import modal_styles2
from flet import *
import asyncio

class ConfirmationModal:
    def __init__(self, page: Page):
        self.page=page

    async def execute_confirmation(self, header_message: str, additional_text: list[str]) -> bool:
        header_text = Text(value=header_message, color="red", size=22) 

        # Get all additional texts into a Text control list
        text = [Text(message) for message in additional_text]

        # Create a future that will be used to store the user's decision
        decision_future = asyncio.get_event_loop().create_future()

        async def remove_cancelled(e):
            if not decision_future.done():
                decision_future.set_result(False)
                self.page.close(modal)

        async def remove_continued(e):
            if not decision_future.done():
                decision_future.set_result(True)
                self.page.close(modal)

        modal_contents = Column(
            controls=[
                header_text,
                *text,
                Row(
                    alignment=MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        OutlinedButton(content=Text("Cancel", color="red"), on_click=remove_cancelled),
                        OutlinedButton(content=Text("Continue"), on_click=remove_continued),
                    ]
                )
            ]
        )

        modal = AlertDialog(
            bgcolor="#00000000",
            modal=False,
            content=Container(
                **modal_styles2(),
                height=150,
                content=modal_contents
            )
        )

        # Show the modal (This should be defined in your framework)
        self.page.open(modal)

        # Wait for the decision to be made
        decision = await decision_future
        return decision