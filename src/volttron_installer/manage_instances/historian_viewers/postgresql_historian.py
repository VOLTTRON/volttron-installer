import asyncio
import json
from volttron_installer.manage_instances import config_store


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _connect(params: dict):
    """Open a read-only psycopg2 connection. Blocking — run in a thread."""
    import psycopg2
    conn = psycopg2.connect(connect_timeout=10, **params)
    conn.set_session(readonly=True)
    return conn


def _to_json_safe(value):
    """Convert non-JSON-native types (datetime, Decimal, etc.) to str."""
    if value is None or isinstance(value, (int, float, bool, str)):
        return value
    return str(value)


# ---------------------------------------------------------------------------
# Discovery (unchanged — reads config via VOLTTRON web API, no DB access)
# ---------------------------------------------------------------------------

async def discover_connection(instance: dict, agent_identity: str, config_name: str = "config") -> dict | None:
    """
    Attempts to read the postgresql historian's connection params from the
    VOLTTRON config store (web API).

    Returns the `connection.params` dict (host, port, dbname, user, password)
    if the agent has a 'postgresql' connection config, or None if unavailable.
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


# ---------------------------------------------------------------------------
# Direct psycopg2 queries — run from the installer host
# ---------------------------------------------------------------------------

def _list_tables_sync(params: dict) -> list:
    conn = _connect(params)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name;"
        )
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


async def list_tables(params: dict) -> list[str]:
    """Lists all user tables in the public schema of the postgres database."""
    try:
        return await asyncio.to_thread(_list_tables_sync, params)
    except Exception as e:
        raise RuntimeError(f"Failed to list tables: {e}")


def _get_table_schema_sync(params: dict, table_name: str) -> list:
    conn = _connect(params)
    try:
        cur = conn.cursor()
        # Validate table exists in public schema
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (table_name,)
        )
        if not cur.fetchone():
            raise ValueError(f"Table {table_name} not found in public schema.")
        cur.execute(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s "
            "ORDER BY ordinal_position;",
            (table_name,)
        )
        return [
            {"name": row[0], "type": row[1], "nullable": row[2], "default": row[3]}
            for row in cur.fetchall()
        ]
    finally:
        conn.close()


async def get_table_schema(params: dict, table_name: str) -> list[dict]:
    """Returns column metadata for the given table (name, type, nullable, default)."""
    try:
        return await asyncio.to_thread(_get_table_schema_sync, params, table_name)
    except Exception as e:
        raise RuntimeError(f"Failed to get table schema: {e}")


def _query_table_sync(params: dict, table_name: str, limit: int, offset: int) -> dict:
    import psycopg2.extras
    conn = _connect(params)
    try:
        cur = conn.cursor()
        # Validate table exists in public schema before interpolating its name
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (table_name,)
        )
        if not cur.fetchone():
            raise ValueError(f"Table {table_name} not found in public schema.")
        # Column order
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s "
            "ORDER BY ordinal_position;",
            (table_name,)
        )
        columns = [row[0] for row in cur.fetchall()]
        # Rows
        dict_cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        dict_cur.execute(
            f'SELECT * FROM "{table_name}" LIMIT %s OFFSET %s;',
            (limit, offset)
        )
        rows = [
            {k: _to_json_safe(v) for k, v in row.items()}
            for row in dict_cur.fetchall()
        ]
        # Total count
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}";')
        total_count = cur.fetchone()[0]
        return {"columns": columns, "rows": rows, "total_count": total_count}
    finally:
        conn.close()


async def query_table(
    params: dict,
    table_name: str,
    limit: int = 500,
    offset: int = 0,
) -> dict:
    """Returns paginated rows from the given table along with total row count."""
    try:
        return await asyncio.to_thread(
            _query_table_sync, params, table_name, int(limit), int(offset)
        )
    except Exception as e:
        raise RuntimeError(f"Failed to query table: {e}")
