import reflex as rx


def text_editor(size="3", placeholder="Type out JSON or upload a file!", **props):
    return rx.text_area(
        width="40rem",
        height="25rem",
        size=size,
        spell_check="false",
        placeholder=placeholder,
        class_name="text_editor",
        **props
    )
