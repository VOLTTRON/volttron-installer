# Upload_config.py
from volttron_installer.modules.prettify_string import prettify_json, prettify_yaml
from .uploading_modal import UploadingModal
from flet import *
import asyncio
import json
import os
import yaml

from volttron_installer.components import uploading_modal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSISTENT_DIR = os.path.join(BASE_DIR, 'uploaded_configs')

class ConfigFilePicker(Control):    
    def __init__(self, page: Page):
        super().__init__()
        self.page = page
        self.file_picker = FilePicker(on_result=self.route_correct_method)
        self.page.overlay.append(self.file_picker)
        self.file_data_future = None

        self.extension_methods: dict[str, callable] = { 
            "csv": self.csv_picker_method,
            "json": self.json_picker_method,
            "yaml": self.yaml_picker_method
        }

        self.modal = UploadingModal(self.page)

    async def route_correct_method(self, e: FilePickerResultEvent) -> None:
        if e.files:
            picked_file = e.files[0]
            print("\nThis is the file we picked:", picked_file)
            print("uploading file...")
            upload_file = FilePickerUploadFile(
                picked_file.name, 
                upload_url=self.page.get_upload_url(picked_file.name, 60)
            )
            self.file_picker.upload([upload_file])
            extension = picked_file.name.split('.')[-1].lower()
            correct_method = self.extension_methods.get(extension)

            print("running modal...")
            asyncio.create_task(self.modal.activate_modal())  # Run modal in the background
            # Update modal text asynchronously
            asyncio.create_task(self.modal.swap_modal_text("Gathering data...", 2))

            print("finding correct method...")
            if correct_method:
                try:
                    data = correct_method(picked_file)
                    print(f"data = correct_method...\ndata: {data}")
                    # Update modal text asynchronously
                    asyncio.create_task(self.modal.swap_modal_text("Parsing data...", 2))
                    
                    if self.file_data_future is None:
                        self.file_data_future = asyncio.get_event_loop().create_future()
                    
                    if not self.file_data_future.done():
                        print("setting future result")
                        self.file_data_future.set_result(data)
                except Exception as exc:
                    print("rejecting future")
                    if self.file_data_future is None:
                        self.file_data_future = asyncio.get_event_loop().create_future()
                    
                    if not self.file_data_future.done():
                        self.file_data_future.set_exception(exc)

    def csv_picker_method(self, data: FilePickerFileType) -> str:
        return ""

    def json_picker_method(self, data: FilePickerFileType) -> str:
        try:
            # Update modal text asynchronously
            asyncio.create_task(self.modal.swap_modal_text("Verifying data..."))
            working_uploaded_file = os.path.join(PERSISTENT_DIR, data.name)
            with open(working_uploaded_file, "r") as f:
                file_contents = json.load(f)
            return ("JSON", file_contents)
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            asyncio.create_task(self.modal.swap_modal_text(f"Error reading file: {data.name}", error=True))
            raise

    def yaml_picker_method(self, data: FilePickerFileType) -> str:
        try:
            working_uploaded_file = os.path.join(PERSISTENT_DIR, data.name)
            with open(working_uploaded_file, "r") as f:
                file_contents = yaml.safe_load(f)
            return ("YAML", file_contents)
        except Exception as e:
            print(f"Error reading YAML file: {e}")
            raise

    async def launch_file_picker(self, allowed_extensions: list[str]):
        self.file_data_future = asyncio.get_event_loop().create_future()
        
        self.file_picker.pick_files(allowed_extensions=allowed_extensions)
        
        try:
            print("we are waiting for data...")
            data = await asyncio.wait_for(self.file_data_future, timeout=30.0)
            print("we are returning data...")
            asyncio.create_task(self.modal.swap_modal_text("Complete!", complete=True))
            return data
        except asyncio.TimeoutError:
            print("File picking timed out")
            asyncio.create_task(self.modal.swap_modal_text("File picking timed out", error=True))
            return None
        except Exception as e:
            print(f"File picking error: {e}")
            return None
