from enum import Enum
from typing import Callable, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, root_validator


class FocusType(str, Enum):
    EXCLUSIVE = "exclusive"
    ON_DEMAND = "on_demand"
    NONE = "none"


class AnchorType(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class LayerType(str, Enum):
    OVERLAY = "overlay"
    TOP = "top"
    BOTTOM = "bottom"
    BACKGROUND = "background"


class Config(BaseModel):
    title: str
    url: Optional[str] = None
    syncDimension: Optional[bool] = Field(default=False)
    inputMask: Optional[bool] = Field(default=False)
    layer: Optional[LayerType] = Field(default=None)
    reserved_space: Optional[int] = None
    anchors: Optional[List[AnchorType]] = Field(default=[])
    top: Optional[int] = None
    bottom: Optional[int] = None
    left: Optional[int] = None
    right: Optional[int] = None
    focus: FocusType = Field(default=FocusType.ON_DEMAND)


class UpdateStrategy(str, Enum):
    MANUAL = "manual"
    ONCE = "once"
    INTERVAL = "interval"
    CONTINOUS = "continous"
    IPC = "ipc"
    DBUS = "dbus"


class State(BaseModel):
    function: str
    updateStrategy: UpdateStrategy
    interval: Optional[int] = None
    script: str
    handler: Callable[[str, Callable[[str], None]], None] = Field(
        default=lambda data, setState: setState(data)
    )

    @root_validator(pre=True)
    def check_interval_condition(cls, values):
        update_strategy = values.get("updateStrategy")
        interval = values.get("interval")

        if update_strategy == "interval" and interval is None:
            raise ValueError(
                "Interval must be provided when updateStrategy is 'interval'."
            )
        return values
