from flet import *
import asyncio
from .common_component_builder.modal import ModalTemplate

class UploadingModal:
    def __init__(self, page: Page, steps: dict[str, int] = {}, clickOff: bool = True, starting_text: str = "") -> None:
        self.page = page
        self.steps = steps
        self.clickOff = clickOff

        self.error_display = Icon(
            name=icons.ERROR_OUTLINE,
            color="red",
            size=26
        )

        self.complete_display = Icon(
            name=icons.CHECK_CIRCLE_OUTLINE, 
            color="green",
            size=26
            )
        
        self.loading_display = ProgressRing(
            width=32,
            height=32
        )

        self.steps_text = Text(value=starting_text)
        self.informational_display = self.loading_display
        self.uploading_modal = self.build_modal()

    async def swap_modal_text(self, text: str, pause: int | float = 0, error: bool = False, complete: bool = False) -> None:
        self.steps_text.value = text
        self.steps_text.update()
        
        if error:
            self.uploading_modal.content.content.content.controls[0] = self.error_display
            self.uploading_modal.update()

        if complete:
            self.uploading_modal.content.content.content.controls[0] = self.complete_display
            self.uploading_modal.update()
        
        self.uploading_modal.content.content.content.controls[0] = self.loading_display


    def build_modal(self):
        modal_content = Container(
            content=Column(
                controls=[
                    self.informational_display,
                    self.steps_text
                ],
                alignment=MainAxisAlignment.CENTER,
                horizontal_alignment=CrossAxisAlignment.CENTER
            ),
            alignment=alignment.center,
            padding=20
        )
        
        modal = ModalTemplate(self.page, modal_content, clickOff=self.clickOff).build_modal()
        return modal
    
    async def activate_modal(self) -> None:
        self.page.open(self.uploading_modal)
