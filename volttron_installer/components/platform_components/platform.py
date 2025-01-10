"""
Using shared instances (Composition) seemed more intuitve because 
as this project grows, it would be easier to use this central psuedo database rather than 
parent class that would need constant re-initalization. The shared Instance uses 1
consistent initialized object making state sharing easy. Each object sharing this shared
instance can read and write to the self.variables, allowing each object to react to the 
state changes very easily while allowing these disconnected objects to be as modular as
possible. In heriently, with a shared isntance structure, communictation between different
modules may be less intuitive than inheritance but i believe that this is solved by the ObjectCommunicator
class, which allows for objects to subscribe to and recieve specific signals so they can execute their
own self.functions() or just interpret the data that have been sent from other modules!
"""
from pprint import pprint
from flet import Page
from volttron_installer.modules.global_configs import global_hosts, global_agents, platforms
from volttron_installer.components.general_notifier import GeneralNotifier
from volttron_installer.modules.write_to_json import write_to_file
import time


class ObjectCommunicator:
    """
    A class for facilitating communication between objects through events or signals.

    This class implements a simple publish-subscribe pattern, allowing objects to subscribe
    to specific events and receive notifications when those events are published.

    Attributes:
        _subscribers (dict): A dictionary storing subscribers for each event type.
            The keys are event types (strings), and the values are lists of callable
            objects (functions or methods) that will be invoked when the event is published.

    Example Usage:

    ```python
    # Create an instance of ObjectCommunicator
    communicator = ObjectCommunicator()

    # Define a subscriber function
    def process_data(data):
        # print(f"Received data: {data}")

    # Subscribe to the 'my_event' event type
    communicator.subscribe('my_event', process_data)

    # Publish the 'my_event' event with some data
    communicator.publish('my_event', "Hello, world!")

    # Output:
    # Received data: Hello, world!
    ```
    """
    def __init__(self):
        """
        Initializes the ObjectCommunicator with an empty subscribers dictionary.
        """
        # { signal : [** list of subscribers' process_data() functions **]}
        self._subscribers = {}

    def subscribe(self, event_type: str, subscriber: callable):
        """
        Subscribes an object to a specific event type.

        Args:
            event_type (str): The event type to subscribe to.
            subscriber (callable): The callable object (function or method) that
                will be invoked when the event is published.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(subscriber)

    def publish(self, event_type, data=None):
        """
        Publishes an event to all subscribers of that event type.

        Args:
            event_type (str): The event type to publish.
            data (any, optional): Data to be passed to the subscribers. Defaults to None.
        """
        if event_type in self._subscribers:
            for subscriber in self._subscribers[event_type]:
                subscriber(data)

class Platform:
    def __init__(self, title: str, page: Page, generated_url: str, event_bus: ObjectCommunicator, global_bus: ObjectCommunicator) -> None:
        self.title = title
        self.page = page
        self.generated_url = generated_url # platform's UID

        self.address = ""
        self.bus_type= "Zmq"
        self.ports = ""

        self.added_hosts = {} # host_id : {key:val, key:val}
        self.added_agents = {} # {agent name : {key: val, key: val}
        # we can use the agent name to parse the agents.json file and get the rest of what we need to deploy


        self.event_bus: ObjectCommunicator = event_bus  # Initialize the Object communicator for all platform components
        self.event_bus.subscribe("deploy_platform", self.deploy_platform)
        
        self.global_bus: ObjectCommunicator = global_bus # Initialize global event bus that observes the state of the app
        self.global_bus.subscribe("update_global_ui", self.update_global_ui)

        self.deployed = False
        self.running = False
        self.activity: str = "OFF"  # OFF by default

        self.snack_bar = GeneralNotifier(self.page)
        self.tile_key: str

    def load_platform(self):
        self.event_bus.publish("load_platform")

    def gather_commits(self):
        self.event_bus.publish("publish_commits")

    def deploy_platform(self, data=None):
        self.gather_commits()
        self.deployed=True

        # TODO
        # fix how this is, i dont like how we need to time.sleep to gather our commits; it should just work fluidly
        time.sleep(2)

        # Debug
        # pprint(f"\n\nDeploying platform with uid of {self.generated_url}")
        # pprint(f"Added Host: {self.added_hosts}")
        # pprint(f"Name: {self.title}")
        # pprint(f"Address: {self.address}")
        # pprint(f"Bus Type: {self.bus_type}")
        # pprint(f"Ports: {self.ports}")
        # pprint(f"Added Agents: {self.added_agents}")
        
        dictionary_appendable = {
            "title" : self.title,
            "deployed" : self.deployed,
            "running" : self.running,
            "address" : self.address,
            "bus_type" : self.bus_type,
            "ports" : self.ports,
            "host" : self.added_hosts,
            "agents" : self.added_agents
        }
        platforms[self.generated_url] = dictionary_appendable
        write_to_file("platforms", platforms)
        self.snack_bar.display_snack_bar("Deployed!")
        # print(platforms)

    def update_global_ui(self, data):
        # Now we are working downwards and telling every component to update their UI
        self.event_bus.publish("update_global_ui", None)

    # Rudimentary code just to see the UI updates of the platform tile in Overview platforms tab 
    def flip_activity(self) -> None:
        self.activity = "OFF" if self.activity == "ON" else "ON"
        # print(f"Platform: I turned activity to: {self.activity}") # Debug # print