# VOLTTRON Installer

The VOLTTRON Installer is a tool designed to simplify the installation and configuration of the VOLTTRON platform, an open-source distributed control system platform for integrating with building systems and devices.

## Overview

The VOLTTRON Installer provides:
- Easy installation of the core VOLTTRON platform
- Automated configuration of various platform components
- Support for both development and production deployments
- Integration with building systems and IoT devices

## Repository Structure

This project depends on several related repositories that are currently under development:

- **volttron-installer** (this repository) - Main installer application
- **eclipse-bacnet-scan-tool** - BACnet device scanning and discovery tool
- **lib-protocol-proxy-fixed** - Core protocol proxy library
- **lib-protocol-proxy-bacnet-fixed** - BACnet-specific protocol proxy implementation

> **Note**: These dependencies are currently in development and not yet published to PyPI. See the [Development Installation](#option-2-development-installation) section for setup instructions.

## System Requirements

### Base System Requirements

When running on bare metal, ensure your system has:

- **Python**: 3.10 or above
- **System Dependencies**:
  ```bash
  sudo apt update
  sudo apt install -y build-essential libffi-dev libssl-dev git python3-dev python3-venv unzip
  ```

### SSH Configuration

The VOLTTRON Installer uses Ansible to deploy VOLTTRON to remote machines over SSH. You need to set up SSH key authentication between:
- **Local machine** - where you run the installer
- **Remote host(s)** - where VOLTTRON will be installed

#### 1. Generate SSH Key (on your local machine)

If you don't already have an SSH key, generate one on the machine where you'll run the installer:

```bash
# Run this on your LOCAL machine (where the installer runs)
ssh-keygen -t rsa
```

*Press Enter to use the default location (`~/.ssh/id_rsa`). You can optionally set a passphrase.*

#### 2. Copy SSH Key to Remote Host(s)

For each remote machine where you want to install VOLTTRON, copy your public key:

```bash
# Run this on your LOCAL machine
# Replace <user> with the username on the remote host
# Replace <remote-host> with the IP address or hostname
ssh-copy-id <user>@<remote-host>
```

This adds your public key to the remote host's `~/.ssh/authorized_keys` file.

#### 3. Verify Connection & Add to Known Hosts

Test the connection and add the remote host to your known_hosts file:

```bash
# Run this on your LOCAL machine
ssh <user>@<remote-host>
```

If the connection succeeds, the remote host is now in your `~/.ssh/known_hosts` file and you can exit.

> **Tip**: If you encounter host key verification issues during deployment, you can enable "Ignore Host Keys" in the platform's advanced settings within the installer UI.


## Installation Options

Important: As of January 2026, installation requires cloning multiple repositories because components are not yet published to PyPI.

1. [**Option 1: Pixi (Recommended)**](#option-1-pixi-recommended) - Easiest setup, handles Python & dependencies automatically.
2. [**Option 2: Manual Development Setup**](#option-2-manual-development-setup) - Requires manually installing Python 3.10 and managing virtualenvs.
3. [**Option 3: VS Code Dev Containers**](#option-3-using-vs-code-dev-containers) - Docker-based isolated environment.

---

### Prerequisites (All Options)

Regardless of the installation method, you must first clone the required repositories into a common workspace.

**Dependency Chain:**
- `volttron-installer` (main project)
  - → `eclipse-bacnet-scan-tool`
    - → `lib-protocol-proxy-fixed`
    - → `lib-protocol-proxy-bacnet-fixed`

**1. Clone Repositories**

You can use the provided helper script to clone all required repositories at once:

```bash
# Make script executable
chmod +x setup-repos.sh

# Run script
./setup-repos.sh
```

Alternatively, you can clone them manually:

```bash
# Create workspace directory
mkdir -p ~/WORK/VOLTTRON
cd ~/WORK/VOLTTRON

# 1. Clone Installer (this repo)
git clone https://github.com/riley206-pnnl/volttron-installer.git
cd volttron-installer
git checkout develop

# 2. Clone Dependencies (siblings in ~/WORK/VOLTTRON/)
cd ~/WORK/VOLTTRON
git clone -b develop https://github.com/riley206-pnnl/eclipse-bacnet-scan-tool.git
git clone -b bus_adapter_changes https://github.com/riley206-pnnl/lib-protocol-proxy-fixed.git
git clone -b merge_of_rileys_code_and_latest_changes https://github.com/riley206-pnnl/lib-protocol-proxy-bacnet-fixed.git
```

> **Note**: These steps are critical. The installer expects these folders to exist at `../[package-name]`.

---

### Option 1: Pixi (Recommended)

[Pixi](https://prefix.dev/) is a package manager that handles Python installation and environment setup automatically. It is the easiest way to get started.

1. **Install Pixi** (if not already installed):
   ```bash
   curl -fsSL https://pixi.sh/install.sh | bash
   source ~/.bashrc
   ```

2. **Install Dependencies & Run**:
   Navigate to the installer directory and use our dev task (installs deps automatically on first run):
   ```bash
   cd ~/WORK/VOLTTRON/volttron-installer
   pixi run dev
   ```

   This single command installs all Python dependencies, the VOLTTRON Ansible collection, and starts the application.

**Available Pixi Tasks:**

| Command | Description |
|---------|-------------|
| `pixi run dev` | Install dependencies (if needed) and run the application |
| `pixi run run` | Run the application (assumes dependencies are installed) |
| `pixi run install-deps` | Install/reinstall all dependencies |
| `pixi run test` | Run the test suite |

---

### Option 2: Manual Development Setup

If you prefer to manage Python manually, you must ensure you are using **Python 3.10**.

**Prerequisites:**
- Python 3.10 (We recommend using [pyenv](https://github.com/pyenv/pyenv))

1. **Create Virtual Environment**:
   ```bash
   cd ~/WORK/VOLTTRON/volttron-installer
   python3.10 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   Install the local packages in editable mode:
   ```bash
   # Install local dependencies
   pip install -e ../lib-protocol-proxy-fixed
   pip install -e ../lib-protocol-proxy-bacnet-fixed
   pip install -e ../eclipse-bacnet-scan-tool
   
   # Install Installer requirements
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Install VOLTTRON Ansible**:
   ```bash
   ansible-galaxy collection install git+https://github.com/eclipse-volttron/volttron-ansible.git,develop
   ```

4. **Run the Application**:
   ```bash
   reflex run
   ```

---

### Option 3: Using VS Code Dev Containers

The project includes a Dev Container configuration for development in Docker.

1. **Open in VS Code**:
   Open the `volttron-installer` folder in VS Code.

2. **Reopen in Container**:
   Run "Remote-Containers: Reopen in Container" from the command palette.

3. **Install Ansible**:
   Once inside the container terminal:
   ```bash
   ansible-galaxy collection install git+https://github.com/eclipse-volttron/volttron-ansible.git,develop
   ```

4. **Testing Pull Requests**:
   ```bash
   test-pr [PR-NUMBER]
   cleanup-pr
   ```

## Usage

After installation, run the VOLTTRON Installer:

```bash
# Using Pixi (recommended)
pixi run dev

# Or if dependencies are already installed
pixi run run

# Or using reflex directly (manual installation)
reflex run
```

The application will start and be available at `http://localhost:3000`. Use the web interface to configure and deploy VOLTTRON platforms to your remote hosts.

## Configuration Options

The installer supports various configuration options:

- Platform installation path
- Message bus configuration
- Agent selection and configuration
- Security settings
- Historian database configuration

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Copyright 2025 Battelle Memorial Institute

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy
of the License at

    http://www.apache.org/licenses/LICENSE-2.0
    
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
