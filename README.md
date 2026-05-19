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

## SSH Deployments

On the New Platform screen, turn off **Install Locally?** and enter the remote host, SSH username, and port.
Remote deployments use SSH key authentication. Create a key on the installer host, add the public key to the
remote user's `~/.ssh/authorized_keys`, and enter the private key path in the installer.

Remote management actions such as start, shutdown, agent install, library install, log tail, and delete run over SSH.
Remote instance pages do not continuously poll SSH-heavy panels; use the refresh buttons for current log, agent,
and library data.
