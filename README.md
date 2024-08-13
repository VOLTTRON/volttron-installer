# Eclipse VOLTRON Platform Installer

## Developer Quick Start

1. Clone the repository
2. Create a python 3.10+ virtual environment inside the volttron-installer directory
3. Activate the environment
4. Execute ```pip install -r requirements.txt``` from the volttron-installer directory
5. Execute ```uvicorn volttron_installer.__main__:app --reload --port 8000
6. Open browser to [https://localhost:8000](https://localhost:8000)

If using visual studio code, a launch.json file has been created.  Instead of step 5 one can
launch the application using the debugger for `launch uvicorn application`.


check list 
[] subscribe every platform to a single object observer instance where additions in the agent setup and hosts will publish
	a signal and every platform will update their check boxes

[] clicking on an agent in agent config should bring up their agent specific configuration store underneath.


issues:

[] when you populate either the hosts or agent setup in the respective global pages in Overview, once you decide
to take a look at a platform's view and go back to the host or agents page in Overview, their tiles disapear.

<!-- # volttron-installer
### Installing Prerequisites
1. Ensure that Python version 3.10[^1] is installed by running `python3.10 --version`
   - If Python 3.10 is not installed, add the deadsnakes PPA by running `sudo add-apt-repository ppa:deadsnakes/ppa`
   - Run `sudo apt update` to refresh the cache
   - Install Python 3.10 by running `sudo apt install python3.10`
   - Validate that Python 3.10 was installed by running `python3.10 --version`
2. Ensure that curl is installed on the system by running `curl --version`
   - If curl is not installed, run `sudo apt install curl` to install it
### Running the Script
1. Run the command `python3 <(curl -sSL https://raw.githubusercontent.com/VOLTTRON/volttron-installer/develop/web.py)`
   - Installs the ansible, git, pexpect, pip and python3.10-venv packages if they are not already installed
   - Creates and activates a virtual environment in the directory where the script was ran
   - Installs the volttron-ansible collection
   - Prompts user to choose the amount of instances they want installed (maximum of 5)
   - Starts a web server and opens the default browser, pointing to 'http://localhost:8080'
2. Navigating the Web Page - 1 instance
   - Enter password then click 'Install Base Requirements' to install what is needed for volttron
   - After the base requirements have been installed, click 'Create Instance' to create and run the instance
   - After installation, pick whatever services are needed for the instance and click 'Install Services'
   - Start and stop buttons for the instance are show on the bottom of the page
3. Navigating the Web Page - Multiple Instances
   - Pick what services are needed for each instance and click 'Configure Instance'
   - Navigate to the bottom of the page to enter your password, then click 'Install All Instances'
   - Start and stop buttons are provided under 'Configure Instance' for each instance
[^1]: Any version of Python greater than 3.8 will work -->
