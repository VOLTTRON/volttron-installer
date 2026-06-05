from nicegui import core, ui


_dark_mode_value = False


def _remember_theme(event):
    global _dark_mode_value
    _dark_mode_value = event.value
    core.app.config.dark = event.value


def dark_mode():
    """Return a dark-mode controller initialized from the app's last choice."""
    return ui.dark_mode(value=_dark_mode_value, on_change=_remember_theme)


def page_container(*extra: str) -> str:
    return ' '.join(('w-full items-center min-h-screen', *extra))


def card(*extra: str) -> str:
    return ' '.join(('w-full p-6', *extra))


def dialog_card(*extra: str) -> str:
    return ' '.join(('p-6 gap-4', *extra))


def title(*extra: str) -> str:
    return ' '.join(('text-4xl font-bold', *extra))


def section_title(*extra: str) -> str:
    return ' '.join(('text-xl font-semibold', *extra))


def muted(*extra: str) -> str:
    return ' '.join(('text-grey-6', *extra))


def small_muted(*extra: str) -> str:
    return muted('text-sm', *extra)
