from flet import Control

def attempt_to_update_control(control: Control)->None:
    if control.page:
        try:
            control.update()
        except Exception as ex:
            print(f"Unexpected error updating control at memory address: {control}", ex)