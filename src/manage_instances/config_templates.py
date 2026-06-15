TEMPLATES = {
    "SQLite Historian": {
        "name": "config",
        "type": "application/json",
        "content": {
            "connection": {
                "type": "sqlite",
                "params": {
                    "database": "data/historian.sqlite"
                }
            }
        }
    }
}