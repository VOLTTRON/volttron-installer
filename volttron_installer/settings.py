from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load dev environment variables if dev.env exists otherwise
# load production .env file
if Path("dev.env").exists():
    load_dotenv("dev.env")
elif Path(".env").exists():
    load_dotenv()
else:
    raise FileNotFoundError("No .env nore dev.env file found")


class _InstallerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VI_")

    log_level: str = Field(default="DEBUG")
    secret_key: str = Field()
    app_name: str = Field()
    upload_dir: str = Field()
    data_dir: str = Field()

    def model_post_init(self, __context):
        if upload_dir := self.upload_dir:
            upload_dir = Path(upload_dir).expanduser()
            if not upload_dir.exists():
                upload_dir.mkdir(parents=True)
            self.upload_dir = upload_dir.as_posix()
        if inventory_data_dir := self.data_dir:
            inventory_data_dir = Path(inventory_data_dir).expanduser()
            if not inventory_data_dir.exists():
                inventory_data_dir.mkdir(parents=True)
            self.data_dir = inventory_data_dir.as_posix()


__settings__ = _InstallerSettings()
def get_settings() -> _InstallerSettings:
    return __settings__

