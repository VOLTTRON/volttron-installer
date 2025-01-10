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

## Brief Overview

On launch, the user is greeted to an `Overview` page with tabs. These tabs house several key pages like `Platforms`- which displays all the platforms registered, `Agent Setup`- a page where a user can setup an agent, `Hosts`- a page displaying all registered pages and where you can edit and deploy new pages, and `Config Store Manager`- a page where you can edit, add, and delete configs that should serve as defaults when registering a config to an agent.

On the top right is a button to add a blank slate of a platform. Clicking on this button produces a tile in the `Platforms` tab, this tile routes to the platforms specific page where 2 more tabs are present. `Platform Config` - a page where you can configure a platform under a host and bind agents, and `Agent Config` - a tab where you can select an agent, configure that agent with custom JSON or scroll down to an agents specific `Config Store Manager` where you can edit agent specific drivers. Once you have properly set up an Platform, the deploy platform button on the header should be available to you and you should be able to deploy your platform

## Technical Overview

Routing happens in the `__init__.py` file where it displays our `home.py`/Overview page. Our dynamically routered pages also are managed in this `__init__.py` file. Dynamic routes are created once a `PlatformTile` instance is created in the home page.

Each program tile instance houses their own view and each of these views are their own objects. These objects communicate through a shared `Platform` instance with `ObjectCommunicator` acting as their event bus allowing for a shared state and efficient way of writing and reading from a central, what i deem a, __pseudo database__. You can see how it works under `components/platform_components/platform.py` and inspecting how `platform_tabs/agent_config.py` or `platform_tabs/platform_config.py` use the shared instance with something like ctrl + F __self.platform__.

## Noticable Flaws Within Code Base

There is lots of confusing structure design going on. For example, in `platform_tile.py`, the whole page platform routing and display happens in this file even though the name suggests it would be more or less a component. This file also is the constructor for the program view's tabs. Taking a look at the section in `ProgramTile` instance where the `PlatformConfig` instance is created, you see that we pass in containers and text fields. This doesn't really make sense because we can still pass everything up into the main shared instance of `Program`. And to write to the shared instance we would simply have something like `self.program.address = textfield.value`. Everything still works but realistically the only thing that needs to be passed is the shared instance.

The whole `components/platformcomponents` dir is just so weird... platform.py isnt even a component its so much more and i dont even know why `agent.py` is even in `componenets/` either i messed up a little bit

There is also a lot of redundant files which in my opinion clutter up the workspace. Files like `config_manager.py` and `platform_manager.py` under `views` have no use.

The main overview tabs withing the `views` dir, `global_config_store.py`, `agent_setup.py`, and `host_tabs.py` all share really similar code. Their forms are really similarly coded and it would be nice to break it apart. But they work nonetheless.

## Developer checklist

- [x] Have a way to update all UI components with any additions or edits to the `global_hosts`, `global_drivers`, or `global_agents` variables under `/modules/global_configs` | One way I've thought about going about this was to create some sort of observer instance for each of these variables and have each platform subscribe to a signal like "update_global_ui" and once this observer instance sees changes, publishes the "update_global_ui" signal. These signals could all be possible with the `class ObjectCommunicator` in `platform.py` most likely by instantiating one instance of Object Communicator and passing it into the `Platform` object as well as the observer instance object we've been talking about.

- [ ] inside a `PlatformTile` instance, clicking on an agent in agent config should bring up their agent specific configuration store underneath.

- [ ] inside a `PlatformTile` instance, we need to deem what are the suitable requirements for a platform to be deployed and be able to deploy a platform and write that instance to `platforms.json`

- [ ] In the overview page, `config_store_manager` we need to add a text box or something to edit the configuration of a driver.

- [ ] In `Agent Setup` tab in overview, when clicking on the modal in the form, we need to have a dropdown with all the available drivers that are registered within the `Config Store Manager`. From there, we can edit the driver to the agent's specific needs. Inside `views/agent_setup.py` and under the `Agent` class, there should be a new attribute like `driver_custom_config` and it should be pretty easy to differentiate whether or not it is a csv or json config. with this config we could write to the agents.json file with its custom driver configs.

## issues

- when you populate either the hosts or agent setup in the respective global pages in Overview, once you decide
to take a look at a platform's view and go back to the host or agents page in Overview, their tiles disappear.

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
