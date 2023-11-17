from subprocess import Popen, PIPE, check_output

import os
import time
import sys

# Variables for package installation
ansible_installed = False
git_installed = False
nicegui_installed = False
pip_installed = False
pexpect_installed = False
pexpect_upgraded = False
venv_installed = False

# Check python version. If not 3.10, prompt user to download Python 3.10 and exit program
python_version_cmd = Popen(["bash", "-c", "python3.10 -V"], stdout=PIPE, stderr=PIPE)
python_version = python_version_cmd.stdout.read().decode("utf-8")
if not python_version.startswith("Python 3.10"):
    print("Python 3.10 has not been installed. Please install Python 3.10 before continuing.")
    print("Exiting...")
    sys.exit(1)

"""
    Checks whether a virtual environment under .venv exists in the current directory; 
    If not, create a virtual environment under the current directory as .venv;
    If there is a virtual environment under .venv, ask the user if they want to 
    override the current .venv or name the virtual environment as something else.
"""
print("Now checking if the virtual environment '.venv' exists.")
time.sleep(1)
if not os.path.exists(".venv"):
    venv_name = ".venv"
    print("The virtual environment '.venv' does not exist. Now creating the virtual environment as '.venv'.")
    Popen(["bash", "-c", "python3.10 -m venv .venv"]).wait()
    print("The virtual environment '.venv' has been created.")
elif os.path.exists(".venv"):
    while True:
        override = str(input("The virtual environment '.venv' does exist. Would you like to override it? (yes or no) "))
        if override.upper().startswith("Y"):
            venv_name = ".venv"
            print("Now overriding the current virtual environment.")
            Popen(["bash", "-c", "python3.10 -m venv .venv"]).wait()
            print("The virtual environment '.venv' has been created and has overridden the previous virtual environment.")
            break
        elif override.upper().startswith("N"):
            venv_name = str(input("What would you like the new virtual environment to be named? "))
            print(f"Now creating the virtual environment '{venv_name}'.")
            Popen(["bash", "-c", f"python3.10 -m venv {venv_name}"]).wait()
            print(f"The virtual environment '{venv_name}' has been created.")
            break
        else:
            print("Please enter yes or no.")

# Check if the required packages are installed; Install the packages if uninstalled
print("Checking if the required packages are installed.")
time.sleep(0.5)

dpkg_output = check_output(["dpkg", "-l"])
packages = [line.split()[1] for line in dpkg_output.decode().splitlines() if line.startswith("ii")]

pexpect_version_cmd = Popen(["bash", "-c", f"source {venv_name}/bin/activate && pip freeze | grep pexpect"], stdout=PIPE, stderr=PIPE)
pexpect_version = pexpect_version_cmd.stdout.read().decode("utf-8")

nicegui_cmd = Popen(["bash", "-c", f"source {venv_name}/bin/activate && pip freeze | grep nicegui"], stdout=PIPE, stderr=PIPE)
nicegui_version = nicegui_cmd.stdout.read().decode("utf-8")

for package in packages:
    if package == "ansible":
        ansible_installed = True
    if package == "git":
        git_installed = True
    if package == "nicegui":
        nicegui_installed = True
    if package == "python3-pip":
        pip_installed = True
    if package == "python3.10-venv":
        venv_installed = True

if "nicegui" in nicegui_version:
    nicegui_installed = True

if pexpect_version.startswith("pexpect==4"):
    pexpect_installed = True
    pexpect_upgraded = True
elif not pexpect_version.startswith("pexpect==4"):
    pexpect_installed = True
    pexpect_upgraded = False

if not ansible_installed:
    print("Ansible has not been installed. Now installing the ansible package using apt.")
    Popen(["bash", "-c", "sudo apt-get install -y ansible"]).wait()
    print("Ansible has now been installed.")
elif ansible_installed:
    print("Ansible is already installed.")

if not git_installed:
    print("Git has not been installed. Now installing the git package using apt.")
    Popen(["bash", "-c", "sudo apt-get install -y git"]).wait()
    print("Git has now been installed.")
elif git_installed:
    print("Git is already installed.")

if not nicegui_installed:
    print("NiceGUI has not been installed. Now installing the NiceGUI package with pip")
    Popen(["bash", "-c", f"source {venv_name}/bin/activate && pip install nicegui"]).wait()
    print("NiceGUI has been installed")
elif nicegui_installed:
    print("NiceGUI is already installed")

if not pip_installed:
    print("Pip has not been installed. Now installing the pip package using apt.")
    Popen(["bash", "-c", "sudo apt install python3-pip"]).wait()
    print("Pip has now been installed.")
elif pip_installed:
    print("Pip is already installed.")

if not pexpect_installed:
    print("Pexpect has not been installed. Now installing the pexpect package.")
    Popen(["bash", "-c", f"source {venv_name}/bin/activate && pip install pexpect"]).wait()
    print("Pexpect has been installed to its latest version.")
elif pexpect_installed and not pexpect_upgraded:
    print("Pexpect is installed but is not the correct version. Now updating the pexpect package.")
    Popen(["bash", "-c", f"source {venv_name}/bin/activate && pip install --upgrade pexpect"]).wait()
    print("Pexpect has been upgraded to its latest version.")
elif pexpect_installed and pexpect_upgraded:
    print("Pexpect has already been installed")

if not venv_installed:
    print("Python3.10-venv has not been installed. Now installing the python3.10-venv package using apt.")
    Popen(["bash", "-c", "sudo apt-get install -y python3.10-venv"]).wait()
    print("Python3.10-venv has now been installed.")
elif venv_installed:
    print("Python3.10-venv is already installed.")

# Activate the virtual environment and install volttron-ansible depending on whether the venv was overriden or not.
print("Now checking if the collection 'volttron-ansible' is installed.")
time.sleep(1)
if not os.path.exists(os.path.expanduser("~/.ansible/collections/ansible_collections/volttron")):
    print("The collection 'volttron-ansible' has not been installed.")
    print(f"Now activating the virtual environemnt '{venv_name}' and installing the collection 'volttron-ansible'.")
    Popen(["bash", "-c", f"source {venv_name}/bin/activate && ansible-galaxy collection install git+https://github.com/VOLTTRON/volttron-ansible.git,develop"]).wait()
    print(f"The collection 'volttron-ansible' has been installed inside the virtual environment '{venv_name}'.")
else:
    print("The collection 'volttron-ansible' is already installed.")

# Clone repo so web server can access files related to the web server
print("Cloning volttron-installer repository so the web server can access required files")
Popen(["bash", "-c", "git clone --branch niceGUI https://github.com/VOLTTRON/volttron-installer.git"]).wait()

# Start NiceGUI
Popen(['bash', '-c', f'source {venv_name}/bin/activate && python3 volttron-installer/pages.py']).wait()