# volttron-installer
### Installing Prerequisites
1. Ensure that Python version 3.10[^1] is installed by running `python3.10 --version`
   - If Python 3.10 is not installed, add the deadsnakes PPA by running `sudo add-apt-repository ppa:deadsnakes/ppa`
   - Run `sudo apt update` to refresh the cache.
   - Install Python 3.10 by running `sudo apt install python3.10`
   - Validate that Python 3.10 was installed by running `python3.10 --version`
2. Ensure that curl is installed on the system by running `curl --version`
   - If curl is not installed, run `sudo apt install curl` to install it.
### Running the Script
1. Run the command `python3 <(curl -sSL https://raw.githubusercontent.com/VOLTTRON/volttron-installer/niceGUI/main.py)`
   - Installs the ansible, git, nicegui, pexpect, pip and python3.10-venv packages if they are not already installed.
   - Creates and activates a virtual environment in the directory where the script was ran.
   - Installs the volttron-ansible collection.
   - Clones this directory to access files required for the GUI to run.
   - Starts a web server and opens the default browser, pointing to 'http://127.0.0.1:8080'
2. Navigating the Web Page
   - The header can be used to access the home page, machines page, and instances page.
   - The home page shows deployed machines with the instances that are binded to their IP's.
   - The machines page displays all machines added and can be used to add/remove more machines.
   - The instances page displays all instances added and can be used to add/edit/remove more instances.
[^1]: Any version of Python greater than 3.8 will work
