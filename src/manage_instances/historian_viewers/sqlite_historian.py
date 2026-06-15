import json
from src.manage_instances.historian_viewers.base import execute_python_code

async def find_databases(instance: dict) -> list[str]:
    """
    Finds all SQLite database files under the instance's VOLTTRON_HOME.
    """
    volttron_home = instance.get("volttron_home") or ""
    if not volttron_home:
        return []

    code = f"""
import os, json
volttron_home = os.path.expanduser({repr(volttron_home)})
results = []
if os.path.isdir(volttron_home):
    for root, dirs, files in os.walk(volttron_home):
        for file in files:
            if file.endswith('.sqlite') or file.endswith('.db'):
                results.append(os.path.abspath(os.path.join(root, file)))
print(json.dumps(results))
"""
    try:
        output = await execute_python_code(instance, code)
        return json.loads(output.strip())
    except Exception:
        return []

async def list_tables(instance: dict, db_path: str) -> list[str]:
    """
    Lists all tables in the specified SQLite database.
    """
    code = f"""
import sqlite3, json
db_path = {repr(db_path)}
try:
    conn = sqlite3.connect(f"file:{{db_path}}?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    print(json.dumps({{"success": True, "tables": tables}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
    try:
        output = await execute_python_code(instance, code)
        res = json.loads(output.strip())
        if not res.get("success"):
            raise RuntimeError(res.get("error", "Unknown error listing tables"))
        return res.get("tables", [])
    except Exception as e:
        raise RuntimeError(f"Failed to list tables: {e}")

async def get_table_schema(instance: dict, db_path: str, table_name: str) -> list[dict]:
    """
    Gets the schema (columns) of the specified table.
    """
    code = f"""
import sqlite3, json
db_path = {repr(db_path)}
table_name = {repr(table_name)}
try:
    conn = sqlite3.connect(f"file:{{db_path}}?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    if table_name not in tables:
        raise ValueError(f"Table {{table_name}} not found in database.")
    
    cursor.execute(f"PRAGMA table_info({{table_name}});")
    columns = []
    for row in cursor.fetchall():
        columns.append({{
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": row[3],
            "dflt_value": row[4],
            "pk": row[5]
        }})
    conn.close()
    print(json.dumps({{"success": True, "columns": columns}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
    try:
        output = await execute_python_code(instance, code)
        res = json.loads(output.strip())
        if not res.get("success"):
            raise RuntimeError(res.get("error", "Unknown error getting schema"))
        return res.get("columns", [])
    except Exception as e:
        raise RuntimeError(f"Failed to get table schema: {e}")

async def query_table(instance: dict, db_path: str, table_name: str, limit: int = 100, offset: int = 0) -> dict:
    """
    Queries rows from the specified table.
    """
    code = f"""
import sqlite3, json
db_path = {repr(db_path)}
table_name = {repr(table_name)}
limit = {int(limit)}
offset = {int(offset)}
try:
    conn = sqlite3.connect(f"file:{{db_path}}?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    if table_name not in tables:
        raise ValueError(f"Table {{table_name}} not found in database.")
    
    cursor.execute(f"PRAGMA table_info({{table_name}});")
    columns = [row[1] for row in cursor.fetchall()]
    
    cursor.execute(f"SELECT * FROM {{table_name}} LIMIT ? OFFSET ?;", (limit, offset))
    rows = []
    for row in cursor.fetchall():
        rows.append(dict(zip(columns, row)))
        
    cursor.execute(f"SELECT COUNT(*) FROM {{table_name}};")
    total_count = cursor.fetchone()[0]
    
    conn.close()
    print(json.dumps({{"success": True, "columns": columns, "rows": rows, "total_count": total_count}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
    try:
        output = await execute_python_code(instance, code)
        res = json.loads(output.strip())
        if not res.get("success"):
            raise RuntimeError(res.get("error", "Unknown error querying table"))
        return {
            "columns": res.get("columns", []),
            "rows": res.get("rows", []),
            "total_count": res.get("total_count", 0)
        }
    except Exception as e:
        raise RuntimeError(f"Failed to query table: {e}")