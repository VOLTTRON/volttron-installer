# VOLTTRON Installer

The VOLTTRON Installer is a tool designed to simplify the installation and configuration of the VOLTTRON platform, an open-source distributed control system platform for integrating with building systems and devices.

## Overview

The VOLTTRON Installer provides:
- Easy installation of the core VOLTTRON platform
- Automated configuration of various platform components
- Support for both development and production deployments
- Integration with building systems and IoT devices

## System Requirements

### Base System Requirements

When running on bare metal, ensure your system has:

- **Python**: 3.10 or above
- **System Dependencies**:
  ```bash
  sudo apt update
  sudo apt install -y build-essential libffi-dev libssl-dev git python3-dev python3-venv unzip
  ```

## Installation Options

### Option 1: Direct Installation with Pip

1. **Create a Virtual Environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install VOLTTRON Installer**
   ```bash
   pip install git+https://github.com/VOLTTRON/volttron-installer.git@develop
   ```
3. **Install VOLTTRON Ansible**
      
      ```bash
      ansible-galaxy collection install git+https://github.com/eclipse-volttron/volttron-ansible.git@develop
      ```
      *For more information, see the VOLTTRON Ansible repository at https://github.com/eclipse-volttron/volttron-ansible.git*

4. **Run the Installer**
   ```bash
   reflex run
   ```

### Option 2: Development Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/VOLTTRON/volttron-installer.git
   cd volttron-installer
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install in Development Mode**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
4. **Install VOLTTRON Ansible**
      ```bash
      ansible-galaxy collection install git+https://github.com/eclipse-volttron/volttron-ansible.git@develop
      ```
      *For more information, see the VOLTTRON Ansible repository at https://github.com/eclipse-volttron/volttron-ansible.git*
5. **Run the Installer**
   ```bash
   reflex run
   ```

### Option 3: Using VS Code Dev Containers

The repository includes a Dev Container configuration that allows you to develop and test the project in a consistent environment.

#### Prerequisites

- [VS Code](https://code.visualstudio.com/download)
- [Docker](https://docs.docker.com/get-docker/)
- [VS Code Remote - Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

#### Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/VOLTTRON/volttron-installer.git
   cd volttron-installer
   ```
2. **Install VOLTTRON Ansible**
      ```bash
      ansible-galaxy collection install git+https://github.com/eclipse-volttron/volttron-ansible.git@develop
      ```
   *For more information, see the VOLTTRON Ansible repository at https://github.com/eclipse-volttron/volttron-ansible.git*

3. **Open in VS Code**
   ```bash
   code .
   ```

4. **Reopen in Container**
   When prompted by VS Code, click "Reopen in Container" or use the command palette (F1) and select "Remote-Containers: Reopen in Container".

5. **Testing Pull Requests**
   Once the container is running, you can test pull requests using the included script:
   ```bash
   test-pr [PR-NUMBER]
   ```

6. **Clean Up After Testing**
   When finished testing, clean up using:
   ```bash
   cleanup-pr
   ```

## Usage

After installation, run the VOLTTRON Installer:

```bash
reflex run
```

Follow the interactive prompts to configure your VOLTTRON installation.

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
