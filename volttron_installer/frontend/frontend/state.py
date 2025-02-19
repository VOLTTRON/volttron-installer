import reflex as rx

class HostState(rx.State):
    host_id_value: str = ""
    ssh_sudo_user_value: str = ""
    identity_file_value: str = "~/.ssh/rsa"
    ssh_ip_address_value: str = ""
    ssh_port_value: str = ""
    
    @rx.event
    def changing_state_values(self, state_value: str, change: str):
        # Directly modify the state value
        setattr(self, state_value, change)