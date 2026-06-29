from nicegui import ui
from src.dark import dark_mode_control


# ---------------------------------------------------------------------------
# Feature card definitions
# ---------------------------------------------------------------------------

_FEATURES = [
    {
        'icon': 'rocket_launch',
        'icon_color': 'primary',
        'title': 'Deploy a Platform',
        'description': (
            'Install a new VOLTTRON instance locally or on a remote machine over SSH. '
            'Supports both modular and monolithic configurations.'
        ),
        'cta': 'Deploy Now',
        'route': '/deploy',
    },
    {
        'icon': 'dns',
        'icon_color': 'secondary',
        'title': 'Manage Instances',
        'description': (
            'View, start, stop, and configure your deployed platforms. '
            'Install and remove agents, manage libraries, and view live logs.'
        ),
        'cta': 'View Instances',
        'route': '/instances',
    },
    {
        'icon': 'travel_explore',
        'icon_color': 'accent',
        'title': 'BACnet Scan',
        'description': (
            'Discover BACnet devices on your network and automatically build '
            'agent configuration bundles ready for deployment.'
        ),
        'cta': 'Open Scanner',
        'route': '/bacnet_scan',
    },
]


# ---------------------------------------------------------------------------
# Documentation / resource links
# ---------------------------------------------------------------------------

_DOCS = [
    {
        'icon': 'menu_book',
        'label': 'VOLTTRON Docs',
        'url': 'https://eclipse-volttron.readthedocs.io/',
        'subtitle': 'Official documentation site',
    },
    {
        'icon': 'code',
        'label': 'GitHub — Eclipse VOLTTRON',
        'url': 'https://github.com/eclipse-volttron',
        'subtitle': 'Source code and issue tracker',
    },
    {
        'icon': 'integration_instructions',
        'label': 'Modular VOLTTRON Core',
        'url': 'https://github.com/eclipse-volttron/volttron-core',
        'subtitle': 'Modular architecture guide and core repo',
    },
    {
        'icon': 'sensors',
        'label': 'BACnet Driver',
        'url': 'https://github.com/eclipse-volttron/volttron-lib-bacnet-driver',
        'subtitle': 'BACnet driver library and configuration',
    },
    {
        'icon': 'table_chart',
        'label': 'Historian Agents',
        'url': 'https://github.com/eclipse-volttron/volttron-sqlite-historian',
        'subtitle': 'SQLite and PostgreSQL historian repos',
    },
]


# ---------------------------------------------------------------------------
# Getting-started steps
# ---------------------------------------------------------------------------

_STEPS = [
    {
        'icon': 'looks_one',
        'heading': 'Deploy a platform',
        'detail': 'Choose local or SSH, configure your install, and run the Ansible deployment.',
        'cta': 'Deploy',
        'route': '/deploy',
    },
    {
        'icon': 'looks_two',
        'heading': 'Manage your instance',
        'detail': 'Start the platform, install agents and libraries, and confirm it is running.',
        'cta': 'Instances',
        'route': '/instances',
    },
    {
        'icon': 'looks_3',
        'heading': 'Collect & view data',
        'detail': 'Add a historian agent, scan for BACnet devices, and browse your time-series data.',
        'cta': 'BACnet Scan',
        'route': '/bacnet_scan',
    },
]


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _hero() -> None:
    """Title and tagline only — navigation is handled by the feature cards below."""
    with ui.column().classes('items-center gap-4 text-center'):
        ui.label('VOLTTRON Installer').classes('text-5xl font-bold text-primary')
        ui.label('Deploy and manage VOLTTRON platforms from a single interface.').classes(
            'text-lg text-grey-6'
        )


def _feature_cards() -> None:
    """One card per major feature area."""
    ui.label('What you can do').classes('text-2xl font-bold text-center mt-4')

    with ui.row().classes('flex-wrap justify-center gap-6 w-full'):
        for feat in _FEATURES:
            with ui.card().classes('p-6 gap-3 w-64 items-start'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon(feat['icon'], size='lg').props(f'color="{feat["icon_color"]}"')
                    ui.label(feat['title']).classes('text-lg font-semibold')
                ui.label(feat['description']).classes('text-grey-6 text-sm')
                route = feat['route']
                ui.button(
                    feat['cta'],
                    on_click=lambda r=route: ui.navigate.to(r),
                ).props('flat dense').classes('mt-auto self-end')


def _getting_started() -> None:
    """Three-step onboarding card."""
    with ui.card().classes('p-6 gap-4 w-full max-w-2xl'):
        ui.label('Getting Started').classes('text-2xl font-bold')
        ui.label(
            'New to VOLTTRON? Follow these three steps to get up and running.'
        ).classes('text-grey-6')

        ui.separator()

        for step in _STEPS:
            with ui.row().classes('items-start gap-4 w-full'):
                ui.icon(step['icon'], size='md').props('color="primary"')
                with ui.column().classes('gap-1 flex-1'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(step['heading']).classes('font-semibold')
                        route = step['route']
                        ui.button(
                            step['cta'],
                            on_click=lambda r=route: ui.navigate.to(r),
                        ).props('flat dense size="sm"').props('color="primary"')
                    ui.label(step['detail']).classes('text-grey-6 text-sm')


def _doc_links() -> None:
    """Documentation and external resource links."""
    with ui.card().classes('p-6 gap-4 w-full max-w-2xl'):
        ui.label('Documentation & Resources').classes('text-2xl font-bold')
        ui.label(
            'Links to the official VOLTTRON documentation and component repositories.'
        ).classes('text-grey-6')

        ui.separator()

        with ui.column().classes('gap-3 w-full'):
            for doc in _DOCS:
                with ui.row().classes('items-center gap-3'):
                    ui.icon(doc['icon'], size='sm').props('color="primary"')
                    with ui.column().classes('gap-0'):
                        ui.link(doc['label'], doc['url'], new_tab=True).classes(
                            'text-primary font-medium'
                        )
                        ui.label(doc['subtitle']).classes('text-grey-6 text-xs')


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render():
    dark = dark_mode_control()

    # Dark-mode toggle — top-right corner
    with ui.row().classes('absolute top-4 right-4 items-center gap-2'):
        theme_btn = ui.button(on_click=dark.toggle).props('flat round')
        theme_btn.bind_icon_from(dark, 'value', backward=lambda v: 'light_mode' if v else 'dark_mode')

    # Page body — vertically centered, constrained width
    with ui.column().classes(
        'w-full min-h-screen items-center justify-center gap-10 px-4 py-16'
    ):
        with ui.column().classes('items-center gap-10 w-full max-w-5xl'):
            _hero()
            _feature_cards()
            _getting_started()
            _doc_links()
