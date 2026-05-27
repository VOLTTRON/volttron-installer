import asyncio
import logging
import os
import posixpath
import shlex
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TIMEOUT = 600
logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
_HOST_LOCKS: dict[tuple[str, int, str], threading.Lock] = {}
_HOST_LOCKS_GUARD = threading.Lock()


class SSHCommandError(Exception):
    def __init__(self, message: str, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


@dataclass
class SSHCredentials:
    host: str
    username: str
    port: int = 22
    key_path: str | None = None
    password: str | None = None
    ignore_host_keys: bool = False


def is_remote_instance(instance: dict | None) -> bool:
    return bool(instance and not instance.get("is_local", True))


def credentials_from_instance(instance: dict) -> SSHCredentials:
    port_value = instance.get("ssh_port") or instance.get("port") or 22
    try:
        port = int(port_value)
    except (TypeError, ValueError):
        port = 22
    return SSHCredentials(
        host=instance.get("host") or instance.get("ssh_host") or "",
        username=instance.get("ssh_username") or instance.get("username") or "",
        port=port,
        key_path=instance.get("ssh_key_path") or None,
        password=instance.get("ssh_password") or None,
        ignore_host_keys=bool(instance.get("ssh_ignore_host_keys")),
    )


def _host_lock(creds: SSHCredentials) -> threading.Lock:
    key = (creds.host, creds.port, creds.username)
    with _HOST_LOCKS_GUARD:
        if key not in _HOST_LOCKS:
            _HOST_LOCKS[key] = threading.Lock()
        return _HOST_LOCKS[key]


def needs_password(instance: dict | None) -> bool:
    return False


def needs_key(instance: dict | None) -> bool:
    return bool(is_remote_instance(instance) and not instance.get("ssh_key_path"))


def _connect(creds: SSHCredentials):
    try:
        import paramiko
    except ImportError as exc:
        raise SSHCommandError("Paramiko is required for SSH deployments. Install it with `pip install -r requirements.txt`.") from exc

    if not creds.host:
        raise SSHCommandError("Remote host is required.")
    if not creds.username:
        raise SSHCommandError("SSH username is required.")

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    if creds.ignore_host_keys:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.RejectPolicy())

    key_filename = os.path.expanduser(creds.key_path) if creds.key_path else None
    try:
        client.connect(
            hostname=creds.host,
            port=creds.port,
            username=creds.username,
            key_filename=key_filename,
            password=creds.password,
            look_for_keys=not bool(key_filename),
            allow_agent=True,
            timeout=10,
            auth_timeout=30,
            banner_timeout=30,
        )
    except Exception as exc:
        raise SSHCommandError(f"SSH connection failed to {creds.username}@{creds.host}:{creds.port}: {exc}") from exc
    return client


def ensure_local_key_pair(key_path: str) -> tuple[str, str]:
    private_key = Path(os.path.expanduser(key_path)).resolve()
    public_key = private_key.with_name(private_key.name + ".pub")
    if private_key.exists() and public_key.exists():
        return str(private_key), public_key.read_text(encoding="utf-8").strip()
    if private_key.exists():
        public_text = subprocess.check_output(
            ["ssh-keygen", "-y", "-f", str(private_key)],
            text=True,
        ).strip()
        public_key.write_text(public_text + "\n", encoding="utf-8")
        return str(private_key), public_text

    private_key.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(private_key),
            "-N",
            "",
            "-C",
            "volttron-installer",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return str(private_key), public_key.read_text(encoding="utf-8").strip()


def _install_public_key_sync(instance: dict, public_key: str) -> None:
    creds = credentials_from_instance(instance)
    if not creds.password:
        raise SSHCommandError("Temporary SSH password is required to install the SSH key.")

    with _host_lock(creds):
        client = _connect(creds)
        try:
            escaped_key = shlex.quote(public_key.strip())
            command = (
                "mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
                "touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && "
                f"grep -qxF {escaped_key} ~/.ssh/authorized_keys || "
                f"printf '%s\\n' {escaped_key} >> ~/.ssh/authorized_keys"
            )
            _, stdout, stderr = client.exec_command(f"bash -lc {shlex.quote(command)}", timeout=30)
            stdout.channel.settimeout(30)
            error = stderr.read().decode(errors="replace")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                raise SSHCommandError(error.strip() or "Could not install SSH key.", stderr=error)
        finally:
            client.close()


async def install_public_key(instance: dict, public_key: str) -> None:
    await asyncio.to_thread(_install_public_key_sync, instance, public_key)


def _ensure_passwordless_sudo_sync(instance: dict) -> None:
    creds = credentials_from_instance(instance)
    if not creds.password:
        raise SSHCommandError("Temporary password is required to configure passwordless sudo.")

    safe_name = "".join(ch for ch in creds.username if ch.isalnum() or ch in ("_", "-")) or "volttron"
    sudoers_path = f"/etc/sudoers.d/90-volttron-installer-{safe_name}"
    sudoers_entry = f"{creds.username} ALL=(ALL) NOPASSWD:ALL"
    password = shlex.quote(creds.password)
    entry = shlex.quote(sudoers_entry)
    path = shlex.quote(sudoers_path)
    command = (
        "set -eu; "
        f"printf '%s\\n' {password} | sudo -S -p '' sh -c "
        + shlex.quote(
            f"printf '%s\\n' {entry} > {path} && "
            f"chmod 0440 {path} && "
            f"visudo -cf {path} >/dev/null"
        )
    )

    with _host_lock(creds):
        client = _connect(creds)
        try:
            _, stdout, stderr = client.exec_command(f"bash -lc {shlex.quote(command)}", timeout=30)
            stdout.channel.settimeout(30)
            stdout_text = stdout.read().decode(errors="replace")
            stderr_text = stderr.read().decode(errors="replace")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                detail = stderr_text.strip() or stdout_text.strip() or "Could not configure passwordless sudo."
                raise SSHCommandError(detail, stdout=stdout_text, stderr=stderr_text)
        finally:
            client.close()


async def ensure_passwordless_sudo(instance: dict) -> None:
    await asyncio.to_thread(_ensure_passwordless_sudo_sync, instance)


def _run_sync(instance: dict, command: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    creds = credentials_from_instance(instance)
    with _host_lock(creds):
        client = _connect(creds)
        try:
            _, stdout, stderr = client.exec_command(
                f"bash -lc {shlex.quote(command)}",
                timeout=timeout,
                get_pty=False,
            )
            stdout.channel.settimeout(timeout)
            stderr.channel.settimeout(timeout)
            stdout_text = stdout.read().decode(errors="replace")
            stderr_text = stderr.read().decode(errors="replace")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                detail = stderr_text.strip() or stdout_text.strip() or f"Command exited with {exit_status}"
                raise SSHCommandError(detail, stdout=stdout_text, stderr=stderr_text)
            return stdout_text, stderr_text
        finally:
            client.close()


async def run(instance: dict, command: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    return await asyncio.to_thread(_run_sync, instance, command, timeout)


async def test_connection(instance: dict) -> str:
    stdout, _ = await run(instance, "printf 'connected as '; whoami; python3 --version", timeout=30)
    return stdout.strip()


async def expand_path(instance: dict, path_value: str) -> str:
    quoted_path = shlex.quote(path_value or "")
    stdout, _ = await run(
        instance,
        "python3 -c "
        + shlex.quote("import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))")
        + f" {quoted_path}",
        timeout=30,
    )
    return stdout.strip()


def _mkdir_p_sftp(sftp, remote_dir: str) -> None:
    remote_dir = posixpath.normpath(remote_dir)
    if remote_dir in {"", "/"}:
        return
    parts = remote_dir.strip("/").split("/")
    current = ""
    for part in parts:
        current += "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def _write_text_sync(instance: dict, remote_path: str, content: str, mode: int | None = None) -> None:
    creds = credentials_from_instance(instance)
    with _host_lock(creds):
        client = _connect(creds)
        try:
            sftp = client.open_sftp()
            try:
                stdin, stdout, stderr = client.exec_command(
                    f"bash -lc {shlex.quote('python3 -c ' + shlex.quote('import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))') + ' ' + shlex.quote(remote_path))}",
                    timeout=30,
                )
                expanded_path = stdout.read().decode(errors="replace").strip()
                error = stderr.read().decode(errors="replace").strip()
                if stdout.channel.recv_exit_status() != 0:
                    raise SSHCommandError(error or "Could not expand remote path")
                _mkdir_p_sftp(sftp, posixpath.dirname(expanded_path))
                with sftp.file(expanded_path, "w") as remote_file:
                    remote_file.write(content)
                if mode is not None:
                    sftp.chmod(expanded_path, mode)
            finally:
                sftp.close()
        finally:
            client.close()


async def write_text(instance: dict, remote_path: str, content: str, mode: int | None = None) -> None:
    await asyncio.to_thread(_write_text_sync, instance, remote_path, content, mode)


def _read_text_sync(instance: dict, remote_path: str) -> str:
    creds = credentials_from_instance(instance)
    with _host_lock(creds):
        client = _connect(creds)
        try:
            sftp = client.open_sftp()
            try:
                stdin, stdout, stderr = client.exec_command(
                    f"bash -lc {shlex.quote('python3 -c ' + shlex.quote('import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))') + ' ' + shlex.quote(remote_path))}",
                    timeout=30,
                )
                expanded_path = stdout.read().decode(errors="replace").strip()
                error = stderr.read().decode(errors="replace").strip()
                if stdout.channel.recv_exit_status() != 0:
                    raise SSHCommandError(error or "Could not expand remote path")
                with sftp.file(expanded_path, "r") as remote_file:
                    return remote_file.read().decode(errors="replace")
            finally:
                sftp.close()
        finally:
            client.close()


async def read_text(instance: dict, remote_path: str) -> str:
    return await asyncio.to_thread(_read_text_sync, instance, remote_path)


async def path_exists(instance: dict, remote_path: str) -> bool:
    command = f"test -e {shlex.quote(remote_path)} && printf yes || printf no"
    stdout, _ = await run(instance, command, timeout=30)
    return stdout.strip() == "yes"


async def safe_rmtree(instance: dict, remote_path: str | None) -> str:
    if not remote_path:
        return "No path configured"

    expanded = await expand_path(instance, remote_path)
    home = (await run(instance, "printf %s \"$HOME\"", timeout=30))[0].strip()
    if expanded in {"/", home} or len([part for part in expanded.split("/") if part]) < 2:
        raise SSHCommandError(f"Refusing to delete unsafe remote path: {expanded}")

    stdout, _ = await run(
        instance,
        f"if test -e {shlex.quote(expanded)}; then rm -rf {shlex.quote(expanded)} && printf 'Deleted {expanded}'; else printf 'Skipped missing path: {expanded}'; fi",
        timeout=120,
    )
    return stdout.strip()


async def tail_file(instance: dict, remote_path: str, line_count: int = 200) -> str:
    stdout, _ = await run(
        instance,
        f"if test -f {shlex.quote(remote_path)}; then tail -n {int(line_count)} {shlex.quote(remote_path)}; else printf 'Log file not found at {remote_path}'; fi",
        timeout=30,
    )
    return stdout


async def truncate_file(instance: dict, remote_path: str) -> str:
    stdout, _ = await run(
        instance,
        f"mkdir -p {shlex.quote(posixpath.dirname(remote_path))} && : > {shlex.quote(remote_path)} && printf 'Cleared {remote_path}'",
        timeout=30,
    )
    return stdout.strip()
