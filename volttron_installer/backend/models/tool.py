"""Tool and utility data models."""

from typing import Literal
from pydantic import BaseModel

class ToolRequest(BaseModel):
    # Tool name e.g "bacnet_scan_tool"
    tool_name: str

    # The module path to start a uvicorn app.
    # e.g "bacnet_scan_tool.main:app"
    module_path: str

    # TODO remove all functionality associated with this field within tool router and tool manager
    # this guy causes nothing but errors and should never be true whether or not it needs poetry.
    use_poetry: bool = False


class ToolStatusResponse(BaseModel):
    tool_name: str
    tool_running: bool
    port: int | None


class ConfigStoreEntry(BaseModel):
    """Represents an entry in the configuration store"""
    # path: Annotated[str, AfterValidator(is_valid_field_name_for_config)]
    path: str
    data_type: Literal["CSV", "JSON"] = "JSON"
    value: str = ""

    def to_dict(self)-> dict[str, str]:
        return {
            "path" : self.path,
            "data_type": self.data_type,
            "value": self.value
        }


class SuccessResponse(BaseModel):
    """Simple success response model"""
    success: bool = True
    object: BaseModel = None