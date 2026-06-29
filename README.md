# VOLTTRON NiceGUI Installer & Management Suite

Eclipse VOLTTRON™ (VOLTTRON/volttron) is an open source platform for distributed sensing and control. The platform provides services for collecting and storing data from buildings and devices and provides an environment for developing applications which interact with that data.

[![Eclipse VOLTTRON™](https://img.shields.io/badge/Eclips%20VOLTTRON--red.svg)](https://volttron.readthedocs.io/en/latest/)
![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)
[![pypi version](https://img.shields.io/pypi/v/volttron.svg)](https://pypi.org/project/volttron/)

## Installation

It is recommended to use a virtual environment for installing this application.

```shell
python -m venv env
source env/bin/activate

pip install -r requirements.txt
```

Until these supporting packages are published to PyPI, install them from GitHub:

```bash
ansible-galaxy collection install -f git+https://github.com/riley206-pnnl/volttron-ansible.git,develop
```

```bash
pip install \
  "git+https://github.com/riley206-pnnl/eclipse-bacnet-scan-tool.git@develop" \
  "git+https://github.com/riley206-pnnl/lib-protocol-proxy-bacnet-fixed.git@new_merge_of_rileys_discovery_work" \
  "git+https://github.com/riley206-pnnl/lib-protocol-proxy.git@develop"
```

### Quick Start

1. Start the web interface:
   ```bash
   python main.py
   ```
   The interface will be available at `http://localhost:8080` (or `http://<your-server-ip>:8080`).

2. Create a new platform deployment through the UI and fill in the target host details.

3. Deploy the platform — the installer will use Ansible to create a virtual environment, install modular VOLTTRON packages, and configure a systemd service on the target host.

4. Manage agents, view logs, and configure historians from the instance management pages.

### Optional HTTPS

HTTP is used by default. To start the installer with HTTPS, provide a PEM-encoded certificate and private key:

```bash
export VOLTTRON_INSTALLER_SSL_CERTFILE=/path/to/domain.crt
export VOLTTRON_INSTALLER_SSL_KEYFILE=/path/to/domain.key
python main.py
```

Set `VOLTTRON_INSTALLER_SSL_KEYFILE_PASSWORD` when the private key is encrypted:

```bash
export VOLTTRON_INSTALLER_SSL_KEYFILE_PASSWORD='key-password'
```

To generate a self-signed certificate for testing:

```bash
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -sha256 -days 365 -nodes -subj "/CN=localhost"
```

When HTTPS is enabled, the interface is available at `https://localhost:8080`. Both certificate and key variables are required; otherwise startup fails with a clear error.

## Ansible Deployments

New platform deployments use the modular `volttron.deployment` Ansible collection. When a sibling `../volttron-ansible` checkout is present, the installer uses that local collection so local development changes are picked up. Otherwise it falls back to the `develop` branch:

```bash
ansible-galaxy collection install -f git+https://github.com/riley206-pnnl/volttron-ansible.git,develop
```

The target host must have Python 3.10+, `python3-venv`, pip, git, and systemd available. The Ansible flow:

- Creates a virtual environment on the target host
- Installs the modular VOLTTRON packages
- Writes the platform configuration
- Installs and enables a systemd service
- Configures the web user and VUI REST API when web is enabled
- Starts the platform through systemd

Local and remote deployments need either passwordless sudo or the sudo password entered in Advanced Settings during deployment. The sudo password is only passed to Ansible for that run and is not saved.

Generated inventory and config files are written under `ansible_deployments/` and are local runtime data.

## SSH Management

On the New Platform screen, turn off **Install Locally?** and enter the remote host, SSH username, and port. Remote deployments use SSH key authentication. Create a key on the installer host, add the public key to the remote user's `~/.ssh/authorized_keys`, and enter the private key path in the installer.

Remote management actions such as agent install, library install, log tail, and delete run over SSH. Remote instance pages do not continuously poll SSH-heavy panels; use the refresh buttons for current log, agent, and library data.

## Contributing to VOLTTRON

Please see the [contributing.md](CONTRIBUTING.md) document before contributing to this repository.

Please see [developing_on_modular.md](DEVELOPING_ON_MODULAR.md) document for developing your agents against volttron.

Full VOLTTRON documentation available at [VOLTTRON Readthedocs](https://volttron.readthedocs.io)

# Disclaimer Notice

This material was prepared as an account of work sponsored by an agency of the
United States Government.  Neither the United States Government nor the United
States Department of Energy, nor Battelle, nor any of their employees, nor any
jurisdiction or organization that has cooperated in the development of these
materials, makes any warranty, express or implied, or assumes any legal
liability or responsibility for the accuracy, completeness, or usefulness or any
information, apparatus, product, software, or process disclosed, or represents
that its use would not infringe privately owned rights.

Reference herein to any specific commercial product, process, or service by
trade name, trademark, manufacturer, or otherwise does not necessarily
constitute or imply its endorsement, recommendation, or favoring by the United
States Government or any agency thereof, or Battelle Memorial Institute. The
views and opinions of authors expressed herein do not necessarily state or
reflect those of the United States Government or any agency thereof.
