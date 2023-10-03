from nicegui import ui

import sys

def add_header(page_name: str):
    """Add header"""

    header_items = {
        "Home": "/", 
        "Machines": "/machines", 
        "Instances": "/instances"
        }
    
    with ui.header():
        with ui.row():
            for title, target in header_items.items():
                if title == page_name:
                    ui.link(title, target).style("color: white; text-decoration: none; font-size: 16px; font-weight: bold")
                else: 
                    ui.link(title, target).style("color: white; text-decoration: none; font-size: 16px")