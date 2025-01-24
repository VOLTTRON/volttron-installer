import reflex_chakra as rc
import reflex as rx

class EditableText(rx.ComponentState):
    input: str = ""

    @rx.event
    def set_text(self, value: str):
        self.input = value

    @classmethod
    def get_component(cls, **props):
        return rc.editable(
            rc.editable_input(),
            placeholder=". . .",
            on_submit=cls.set_text,
            width="100%",
            **props
        )