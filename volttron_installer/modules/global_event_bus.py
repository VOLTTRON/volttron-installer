from volttron_installer.components.platform_components.platform import ObjectCommunicator

def create_object_communicator():
    return ObjectCommunicator()

global_event_bus = create_object_communicator()