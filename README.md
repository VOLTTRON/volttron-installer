# VOLTTRON NiceGUI Installer & Management Suite

## Quick Start

### 1. Prerequisites
Make sure you have **Python 3.10+** installed on your host Linux system.

### 2. Installation
Install the required packages in your python environment:
```bash
pip install -r requirements.txt
```

### 3. Run the Installer UI
Start the web interface using:
```bash
python main.py
```
The interface will be hosted locally at `http://localhost:8080` (or `http://<your-server-ip>:8080`).

## Ansible Deployments

New platform deployments use the modular `volttron.deployment` Ansible collection. When a sibling
`../volttron-ansible` checkout is present, the installer installs that local collection so local
development changes are used. Otherwise it falls back to the modular `develop` branch:

```bash
ansible-galaxy collection install -f git+https://github.com/eclipse-volttron/volttron-ansible.git,develop
```

The target host must have Python 3.10+, `python3-venv`, pip, git, and systemd available. The Ansible
flow creates a virtual environment, installs the modular VOLTTRON packages, writes the platform config,
installs a systemd service, enables it, configures the web user and VUI REST API when web is enabled,
and starts the platform through systemd.
Local and remote deployments need either passwordless sudo or the sudo password entered in Advanced
Settings during deployment. The sudo password is only passed to Ansible for that run and is not saved.

Generated inventory/config files are written under `ansible_deployments/` and are local runtime data.

## SSH Management

On the New Platform screen, turn off **Install Locally?** and enter the remote host, SSH username, and port.
Remote deployments use SSH key authentication. Create a key on the installer host, add the public key to the
remote user's `~/.ssh/authorized_keys`, and enter the private key path in the installer.

Remote management actions such as agent install, library install, log tail, and delete run over SSH.
Remote instance pages do not continuously poll SSH-heavy panels; use the refresh buttons for current log, agent,
and library data.
