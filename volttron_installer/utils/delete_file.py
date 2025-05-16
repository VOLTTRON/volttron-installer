import reflex as rx
from loguru import logger
import os 

def delete_file(file_name: str) -> None:
    uploads_dir = rx.get_upload_dir()
    file_path = os.path.join(uploads_dir, file_name)
    if os.path.exists(file_path):
        logger.debug(f"Deleting the file {file_name} from {uploads_dir}.")
        os.remove(file_path)
    else:
        logger.debug(f"The file {file_name} does not exist.")
    return