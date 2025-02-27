from flet import * 
from ...modules.styles import modal_styles2

class ModalTemplate:
    def __init__(
            self, 
            page: Page, 
            content: Control= None,
            clickOff: bool= True
            ):
        self.page=page
        self.content = content 
        if self.content == None:
            self.content = Container()
        self.clickOff=clickOff

    def build_modal(self) -> AlertDialog:
        return AlertDialog(
            bgcolor="#00000000",
            modal= not self.clickOff,
            content=Container(
                **modal_styles2(),
                height=150,
                content=self.content
            )
        )