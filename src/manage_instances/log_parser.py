from nicegui import ui

def push_logs_to_ui(content: str, log_view: ui.log) -> None:
    """
    Parses a block of log content and pushes each line to a NiceGUI ui.log element
    with appropriate color coding based on the log level.
    """
    log_view.clear()
    if not content:
        log_view.push("Log is empty.")
        return
        
    for line in content.splitlines():
        if "ERROR" in line or "CRITICAL" in line:
            log_view.push(line, classes='text-red')
        elif "WARNING" in line:
            log_view.push(line, classes='text-orange')
        elif "DEBUG" in line:
            log_view.push(line, classes='text-grey')
        elif "INFO" in line:
            log_view.push(line, classes='text-blue')
        else:
            log_view.push(line)
