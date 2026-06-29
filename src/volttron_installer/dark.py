from nicegui import ui, app


def dark_mode_control():
    """Create a ui.dark_mode controller bound to per-user storage.

    Persists the user's light/dark preference across page navigations and
    browser reloads via app.storage.user.  Call once at the top of each
    @ui.page render function and use the returned object for the toggle button.
    """
    dark = ui.dark_mode()
    dark.bind_value(app.storage.user, 'dark_mode')
    return dark
