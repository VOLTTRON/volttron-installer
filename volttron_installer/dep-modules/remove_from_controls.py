# flet import statements
from flet import Control, Container

def remove_from_selection(container: Control, index_key: str) -> None:
    """
    Removes a control from a list of controls within a given container, identified by a unique key.

    Args:
        container (Control): The container containing the control to be removed.
        index_key (str): The unique key identifying the control to be removed.

    Returns:
        None
    """
    
    def find_container_index() -> int:
        """
        Finds the index of the container (control) with the unique key.

        Returns:
            int: The index of the control, or -1 if not found.
        """
        for index, control in enumerate(container.controls):
            if isinstance(control, Container) and control.key == index_key:
                return index
        return -1  # Return -1 if the container key is not found

    try:
        # Attempt to find the index of the container with the unique identifier (key)
        container_index = find_container_index()
        if container_index != -1:
            # Remove the control from the container's controls list
            del container.controls[container_index]
            # Update the UI to reflect the change
            container.update()
        else:
            print("The agent row is not found in the container controls list.")
    except ValueError as e:
        print(f"An error occurred: {e}")
        print("The tile row is not found in the container controls list.")
