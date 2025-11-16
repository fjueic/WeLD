from enum import Enum
from typing import Optional


class CliOptions(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    LIST = "list"
    RESTART = "restart"
    LIST_ACTIVE = "listactive"
    SEND = "send"
