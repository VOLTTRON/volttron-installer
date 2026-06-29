import asyncio
import hashlib
import os
import posixpath
import shlex
import sqlite3
import tempfile

from volttron_installer import ssh_remote


# ---------------------------------------------------------------------------
# Local cache helpers
# ---------------------------------------------------------------------------

def _cache_dir() -> str:
    return os.path.join(tempfile.gettempdir(), "volttron-installer-sqlite-cache")


def _cache_path(instance: dict, remote_path: str) -> str:
    """Return a stable local path for the cached copy of a remote DB file."""
    key = hashlib.sha256(
        f"{instance.get('name', '')}::{remote_path}".encode()
    ).hexdigest()[:16]
    filename = f"{key}-{posixpath.basename(remote_path)}"
    return os.path.join(_cache_dir(), filename)


async def _ensure_local_copy(instance: dict, remote_path: str) -> str:
    """
    Return the local filesystem path to use for querying.

    - Local instance: return the path directly (no copy needed).
    - Remote instance: download via SFTP if the remote file has changed
      (size or mtime differs from the cached copy), then return the cache path.
    """
    if not ssh_remote.is_remote_instance(instance):
        return os.path.abspath(os.path.expanduser(remote_path))

    local = _cache_path(instance, remote_path)
    remote_attrs = await ssh_remote.stat(instance, remote_path)

    cached_ok = (
        os.path.exists(local)
        and os.path.getsize(local) == remote_attrs["size"]
        and int(os.path.getmtime(local)) == int(remote_attrs["mtime"])
    )

    if not cached_ok:
        await ssh_remote.download_file(instance, remote_path, local)
        # Stamp the local file with the remote mtime so the next comparison
        # is stable (sftp.get sets local mtime to download time, not source mtime).
        os.utime(local, (remote_attrs["mtime"], remote_attrs["mtime"]))

    return local


# ---------------------------------------------------------------------------
# SQLite query helpers — run blocking sqlite3 work in a thread
# ---------------------------------------------------------------------------

def _list_tables_sync(local_path: str, is_remote: bool) -> list:
    uri = f"file:{local_path}?mode=ro" + ("&immutable=1" if is_remote else "")
    conn = sqlite3.connect(uri, uri=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def _get_table_schema_sync(local_path: str, table_name: str, is_remote: bool) -> list:
    uri = f"file:{local_path}?mode=ro" + ("&immutable=1" if is_remote else "")
    conn = sqlite3.connect(uri, uri=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        if table_name not in tables:
            raise ValueError(f"Table {table_name} not found in database.")
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": row[3],
                "dflt_value": row[4],
                "pk": row[5],
            })
        return columns
    finally:
        conn.close()


def _query_table_sync(local_path: str, table_name: str, limit: int, offset: int, is_remote: bool) -> dict:
    uri = f"file:{local_path}?mode=ro" + ("&immutable=1" if is_remote else "")
    conn = sqlite3.connect(uri, uri=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        if table_name not in tables:
            raise ValueError(f"Table {table_name} not found in database.")

        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [row[1] for row in cursor.fetchall()]

        cursor.execute(
            f"SELECT * FROM {table_name} LIMIT ? OFFSET ?;",
            (limit, offset),
        )
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        total_count = cursor.fetchone()[0]

        return {"columns": columns, "rows": rows, "total_count": total_count}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public async API (same signatures and return shapes as before)
# ---------------------------------------------------------------------------

async def find_databases(instance: dict) -> list[str]:
    """
    Returns a list of absolute paths to SQLite database files under
    the instance's VOLTTRON_HOME.
    """
    volttron_home = instance.get("volttron_home") or ""
    if not volttron_home:
        return []

    if not ssh_remote.is_remote_instance(instance):
        # Local: walk the directory in a thread pool so we don't block the event loop
        def _walk(home):
            home = os.path.abspath(os.path.expanduser(home))
            results = []
            if os.path.isdir(home):
                for root, _dirs, files in os.walk(home):
                    for fname in files:
                        if fname.endswith(".sqlite") or fname.endswith(".db"):
                            results.append(os.path.abspath(os.path.join(root, fname)))
            return results

        try:
            return await asyncio.to_thread(_walk, volttron_home)
        except Exception:
            return []

    # Remote: use `find` over SSH — one shell command, no Python snippet needed
    try:
        expanded_home = await ssh_remote.expand_path(instance, volttron_home)
        cmd = (
            f"find {shlex.quote(expanded_home)} -type f "
            r"\( -name '*.sqlite' -o -name '*.db' \) 2>/dev/null"
        )
        stdout, _ = await ssh_remote.run(instance, cmd, timeout=30)
        return [p for p in stdout.splitlines() if p.strip()]
    except Exception:
        return []


async def list_tables(instance: dict, db_path: str) -> list[str]:
    """Lists all tables in the specified SQLite database."""
    try:
        local = await _ensure_local_copy(instance, db_path)
        is_remote = ssh_remote.is_remote_instance(instance)
        return await asyncio.to_thread(_list_tables_sync, local, is_remote)
    except Exception as e:
        raise RuntimeError(f"Failed to list tables: {e}")


async def get_table_schema(instance: dict, db_path: str, table_name: str) -> list[dict]:
    """Gets the schema (columns) of the specified table."""
    try:
        local = await _ensure_local_copy(instance, db_path)
        is_remote = ssh_remote.is_remote_instance(instance)
        return await asyncio.to_thread(_get_table_schema_sync, local, table_name, is_remote)
    except Exception as e:
        raise RuntimeError(f"Failed to get table schema: {e}")


async def query_table(
    instance: dict,
    db_path: str,
    table_name: str,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Queries rows from the specified table."""
    try:
        local = await _ensure_local_copy(instance, db_path)
        is_remote = ssh_remote.is_remote_instance(instance)
        return await asyncio.to_thread(
            _query_table_sync, local, table_name, int(limit), int(offset), is_remote
        )
    except Exception as e:
        raise RuntimeError(f"Failed to query table: {e}")
