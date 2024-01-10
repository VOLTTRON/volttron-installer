import os
import sys

from subprocess import Popen, PIPE, check_output, check_call

INSTALLER_VENV = ".venv_installer"

def setup_environment():
    if not os.environ.get("VIRTUAL_ENV"):
        # Add virtual env path to environment variable 'VIRTUAL_ENV' to avoid double execution of code block
        #os.environ["VIRTUAL_ENV"] = os.getcwd() + "/.venv_installer"

        # Check python version. If 3.10 is not installed or default, prompt user to download Python 3.10 and exit program
        python_version_cmd = Popen(["bash", "-c", "python3.10 -V"], stdout=PIPE, stderr=PIPE)
        python_version = python_version_cmd.stdout.read().decode("utf-8")
        if not python_version.startswith("Python 3.10"):
            print("Python 3.10 has not been installed. Please install Python 3.10 before continuing.")
            print("Exiting...")
            sys.exit(1)
        
        # Check for git and python3.10-venv before activating virtual environment
        print("Checking if the required packages are installed. (1/2)")
        dpkg_output = check_output(["dpkg", "-l"])
        packages = [line.split()[1] for line in dpkg_output.decode().splitlines() if line.startswith("ii")]
        
        if "git" not in packages:
            print("Git has not been installed. Now installing the git package using apt.")
            Popen(["bash", "-c", "sudo apt-get install -y git"]).wait()
            print("Git has now been installed.")
        else:
            print("Git is already installed.")

        if "python3.10-venv" not in packages:
            print("Python3.10-venv has not been installed. Now installing the python3.10-venv package using apt.")
            Popen(["bash", "-c", "sudo apt-get install -y python3.10-venv"]).wait()
            print("Python3.10-venv has now been installed.")
        else:
            print("Python3.10-venv is already installed.") 

    # We know we are using the right env if it is in the prefix.
    if INSTALLER_VENV not in sys.prefix:
        if not os.path.exists(INSTALLER_VENV):
            result = check_call(["python3.10", "-m", "venv", INSTALLER_VENV])
            if result != 0:
                print("Error creating virtual environment for installer")
                sys.exit(result)   
        result = check_call(['bash', '-c', f'source {INSTALLER_VENV}/bin/activate && {INSTALLER_VENV}/bin/python {sys.argv[0]}'])
        sys.exit(result)
    
    # Check if the required apt packages are installed on system; Install the packages if uninstalled; Done after virtual environment is activated
    print("Checking if the required packages are installed. (2/2)")

    ansible_version_cmd = Popen(["bash", "-c", "pip freeze | grep ansible"], stdout=PIPE, stderr=PIPE)
    ansible_version = ansible_version_cmd.stdout.read().decode("utf-8")

    nicegui_cmd = Popen(["bash", "-c", "pip freeze | grep nicegui"], stdout=PIPE, stderr=PIPE)
    nicegui_version = nicegui_cmd.stdout.read().decode("utf-8")

    pexpect_version_cmd = Popen(["bash", "-c", "pip freeze | grep pexpect"], stdout=PIPE, stderr=PIPE)
    pexpect_version = pexpect_version_cmd.stdout.read().decode("utf-8")

    if not "ansible" in ansible_version:
        print("Ansible has not been installed. Now installing the Ansible package with pip.")
        Popen(["bash", "-c", "pip install ansible"]).wait()
        print("Ansible has been installed")
    else:
        print("Ansible is already installed")

    if not "nicegui" in nicegui_version:
        print("NiceGUI has not been installed. Now installing the NiceGUI package with pip.")
        Popen(["bash", "-c", "pip install nicegui"]).wait()
        print("NiceGUI has been installed")
    else:
        print("NiceGUI is already installed")

    if not "pexpect" in pexpect_version:
        print("Pexpect has not been installed. Now installing the pexpect package with pip.")
        Popen(["bash", "-c", "pip install pexpect"]).wait()
        print("Pexpect has been installed to its latest version.")
    elif "pexpect" in pexpect_version and "pexpect==4" not in pexpect_version:
        print("Pexpect is installed but is not the correct version. Now updating the pexpect package.")
        Popen(["bash", "-c", "pip install --upgrade pexpect"]).wait()
        print("Pexpect has been upgraded to its latest version.")
    else:
        print("Pexpect has already been installed")

    # Install volttron-ansible
    print("Now checking if the collection 'volttron-ansible' is installed.")

    if not os.path.exists(os.path.expanduser("~/.ansible/collections/ansible_collections/volttron")):
        print("The collection 'volttron-ansible' has not been installed.")
        print(f"Now installing the collection 'volttron-ansible'.")
        Popen(["bash", "-c", "ansible-galaxy collection install git+https://github.com/VOLTTRON/volttron-ansible.git,develop"]).wait()
        print(f"The collection 'volttron-ansible' has been installed.")
    else:
        print("The collection 'volttron-ansible' is already installed.")

    # Clone repo so web server can access files related to the web server
    #print("Cloning volttron-installer repository so the web server can access required files")
    #Popen(["bash", "-c", "git clone --branch niceGUI-2.0 https://github.com/VOLTTRON/volttron-installer.git"]).wait()

if __name__ in {"__main__", "__mp_main__"}:
    setup_environment()

    # Create path so directory will be recognized as module
    file_dir = os.path.dirname(os.path.abspath(__file__)) # Directory that houses the main.py file (volttron-installer)
    project_dir = os.path.dirname(file_dir) # Directory that houses project directory
    sys.path.append(project_dir)

    # Import after packages have been installed in virtual environment
    from nicegui import ui
    from new_volttron_installer.pages import Pages # change to volttron-installer

    # Calls show_home function
    Pages.HOME.value.module

    ui.run(reload=False, title="VOLTTRON Deployer") # Set reload to false to stop double execution of script
