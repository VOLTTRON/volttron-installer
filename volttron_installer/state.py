"""Re-exports all state classes for backward compatibility.

State classes are now defined in their own modules under states/.
This file serves as a thin import hub so existing imports continue to work:

    from .state import PlatformPageState, AgentConfigState, etc.
"""

# Module-level dict to track tail processes (can't store in Reflex state)
import subprocess
_tail_processes: dict[str, subprocess.Popen] = {}

# App-level states
from .states.app_state import AppState, ToolState, SettingsState

# Page-level states
from .states.index_state import IndexPageState
from .states.agent_config import AgentConfigState
from .states.bacnet_scan_state import BacnetScanState

# Platform state chain (each inherits from the previous):
# PlatformBaseState -> PlatformLogState -> PlatformStatusState
# -> PlatformAgentState -> PlatformDeploymentState -> DriverManagementState
# -> PlatformCrudState -> PlatformValidationState -> PlatformDialogState
# -> PlatformSaveState -> PlatformPageState(PlatformSaveState)
from .states.platform_base import PlatformBaseState, DevicePlatformGroup
from .states.platform_logs import PlatformLogState
from .states.platform_status import PlatformStatusState
from .states.platform_agent import PlatformAgentState
from .states.platform_deployment import PlatformDeploymentState
from .states.driver_management import DriverManagementState
from .states.platform_crud import PlatformCrudState
from .states.platform_validation import PlatformValidationState
from .states.platform_dialogs import PlatformDialogState
from .states.platform_save import PlatformSaveState


class PlatformPageState(PlatformSaveState):
    """Thin subclass that inherits the full platform page state chain.

    The bulk of the logic lives in the parent classes:
    PlatformBaseState -> PlatformLogState -> PlatformStatusState
    -> PlatformAgentState -> PlatformDeploymentState -> DriverManagementState
    -> PlatformCrudState -> PlatformValidationState -> PlatformDialogState
    -> PlatformSaveState -> PlatformPageState
    """
    pass


__all__ = [
    "AppState",
    "ToolState",
    "SettingsState",
    "IndexPageState",
    "AgentConfigState",
    "BacnetScanState",
    "PlatformBaseState",
    "DevicePlatformGroup",
    "PlatformLogState",
    "PlatformStatusState",
    "PlatformAgentState",
    "PlatformDeploymentState",
    "DriverManagementState",
    "PlatformCrudState",
    "PlatformValidationState",
    "PlatformDialogState",
    "PlatformSaveState",
    "PlatformPageState",
]