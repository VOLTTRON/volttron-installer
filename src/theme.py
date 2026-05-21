from nicegui import ui


_dark_mode_value = True


def _remember_theme(event):
    global _dark_mode_value
    _dark_mode_value = event.value
    theme = 'dark' if event.value else 'light'
    ui.run_javascript(
        f"localStorage.setItem('volttron-theme', '{theme}'); "
        f"document.documentElement.dataset.theme = '{theme}';"
    )


def dark_mode():
    """Return a dark-mode controller initialized from the app's last choice."""
    return ui.dark_mode(value=_dark_mode_value, on_change=_remember_theme)
