import json
import os
from src.manage_instances.historian_viewers.base import execute_python_code
from src.manage_instances import config_store


def _venv_python(instance: dict) -> str | None:
    """Returns the path to the python interpreter in the instance's venv, or None."""
    venv = instance.get("venv") or ""
    if venv:
        return os.path.join(os.path.expanduser(venv), "bin", "python")
    return None


async def discover_connection(instance: dict, agent_identity: str, config_name: str = "config") -> dict | None:
    """
    Attempts to read the postgresql historian's connection params from the config store.

    Returns the `connection.params` dict (host, port, dbname, user, password) if the
    agent has a 'postgresql' connection config, or None if unavailable / not found.
    """
    try:
        content, _ = await config_store.get_config(instance, agent_identity, config_name)
        cfg = json.loads(content)
        conn = cfg.get("connection", {})
        if conn.get("type") == "postgresql":
            return conn.get("params", {})
    except Exception:
        pass
    return None


async def list_tables(instance: dict, params: dict) -> list[str]:
    """
    Lists all user tables in the public schema of the postgres database.
    """
    code = f"""
import psycopg2, json
params = {repr(params)}
try:
    conn = psycopg2.connect(**params)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name;"
    )
    tables = [row[0] for row in cur.fetchall()]
    conn.close()
    print(json.dumps({{"success": True, "tables": tables}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
    try:
        output = await execute_python_code(instance, code, _venv_python(instance))
        res = json.loads(output.strip())
        if not res.get("success"):
            raise RuntimeError(res.get("error", "Unknown error listing tables"))
        return res.get("tables", [])
    except Exception as e:
        raise RuntimeError(f"Failed to list tables: {e}")


async def get_table_schema(instance: dict, params: dict, table_name: str) -> list[dict]:
    """
    Returns column metadata for the given table (name, type, nullable, default).
    table_name must have been retrieved from list_tables — it is never interpolated
    from raw user input.
    """
    code = f"""
import psycopg2, json
params = {repr(params)}
table_name = {repr(table_name)}
try:
    conn = psycopg2.connect(**params)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    # Verify table exists in public schema
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = %s;",
        (table_name,)
    )
    if not cur.fetchone():
        raise ValueError(f"Table {{table_name}} not found in public schema.")
    cur.execute(
        "SELECT column_name, data_type, is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s "
        "ORDER BY ordinal_position;",
        (table_name,)
    )
    columns = [
        {{"name": row[0], "type": row[1], "nullable": row[2], "default": row[3]}}
        for row in cur.fetchall()
    ]
    conn.close()
    print(json.dumps({{"success": True, "columns": columns}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
    try:
        output = await execute_python_code(instance, code, _venv_python(instance))
        res = json.loads(output.strip())
        if not res.get("success"):
            raise RuntimeError(res.get("error", "Unknown error getting schema"))
        return res.get("columns", [])
    except Exception as e:
        raise RuntimeError(f"Failed to get table schema: {e}")


async def query_table(instance: dict, params: dict, table_name: str, limit: int = 500, offset: int = 0) -> dict:
    """
    Returns paginated rows from the given table along with total row count.
    table_name is validated against the live table list in the snippet.
    limit and offset are injected as int literals and also used as psycopg2 params.
    Non-JSON-serialisable values (datetime, Decimal, etc.) are converted to str.
    """
    code = f"""
import psycopg2, json
from psycopg2.extras import RealDictCursor
params = {repr(params)}
table_name = {repr(table_name)}
limit = {int(limit)}
offset = {int(offset)}
try:
    conn = psycopg2.connect(**params)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    # Validate table exists in public schema
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = %s;",
        (table_name,)
    )
    if not cur.fetchone():
        raise ValueError(f"Table {{table_name}} not found in public schema.")
    # Fetch columns
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s "
        "ORDER BY ordinal_position;",
        (table_name,)
    )
    columns = [row[0] for row in cur.fetchall()]
    # Fetch rows using RealDictCursor for named access
    dict_cur = conn.cursor(cursor_factory=RealDictCursor)
    dict_cur.execute(
        f'SELECT * FROM "{{table_name}}" LIMIT %s OFFSET %s;',
        (limit, offset)
    )
    rows = []
    for row in dict_cur.fetchall():
        rows.append({{k: (str(v) if v is not None and not isinstance(v, (int, float, bool, str)) else v) for k, v in row.items()}})
    # Total count
    cur.execute(f'SELECT COUNT(*) FROM "{{table_name}}";')
    total_count = cur.fetchone()[0]
    conn.close()
    print(json.dumps({{"success": True, "columns": columns, "rows": rows, "total_count": total_count}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
    try:
        output = await execute_python_code(instance, code, _venv_python(instance))
        res = json.loads(output.strip())
        if not res.get("success"):
            raise RuntimeError(res.get("error", "Unknown error querying table"))
        return {
            "columns": res.get("columns", []),
            "rows": res.get("rows", []),
            "total_count": res.get("total_count", 0),
        }
    except Exception as e:
        raise RuntimeError(f"Failed to query table: {e}")
