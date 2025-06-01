from enum import Enum
from typing import Callable, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, root_validator

from .loader import AnchorType, FocusType, LayerType


class PayloadType(str, Enum):
    EXEC = "exec"
    MANUAL_STATE_UPDATE = "manual_state_update"
    CLOSE = "close"
    SYNC_DIMENSION = "syncDimension"
    INPUT_MASK = "inputMask"
    APPLY_INPUT_MASK = "applyInputMask"
    REMOVE_INPUT_MASK = "removeInputMask"
    CONFIGURE_FOCUS = "configureFocus"
    CONFIGURE_GTK_LAYER_SHELL = "configureGTKLayerShell"


class ConfigureGTKLayerShellPayloadData(BaseModel):
    layer: Optional[LayerType] = Field(default=None)
    reserved_space: Optional[int] = None
    anchors: Optional[List[AnchorType]] = Field(default=[])
    top: Optional[int] = None
    bottom: Optional[int] = None
    left: Optional[int] = None
    right: Optional[int] = None


class JSMessage(BaseModel):
    name: str
    type: PayloadType
    script: Optional[str] = None
    height: Optional[int] = None
    width: Optional[int] = None
    masks: Optional[List[Tuple[float, float, float, float]]] = None
    function: Optional[str] = None
    focus: Optional[FocusType] = Field(default=FocusType.ON_DEMAND)
    config_layer: Optional[ConfigureGTKLayerShellPayloadData] = None
    args: Optional[dict[str, str]] = {}
