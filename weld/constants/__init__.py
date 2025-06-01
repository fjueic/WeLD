import os
from importlib.resources import files

XDG_CONFIG_HOME: str = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
WIDGET_DIR: str = os.path.join(XDG_CONFIG_HOME, "weld")
SOCKET_PATH: str = "/tmp/weld.sock"
TEXT_ENCODING: str = "utf-8"
SOURCE_HTML: str = "index.html"
SCRIPT_MESSAGE_HANDLER: str = "pybridge"
SCRIPT_MESSAGE_RECEIVED_SIGNAL: str = (
    f"script-message-received::{SCRIPT_MESSAGE_HANDLER}"
)


# Web injection files
SYNC_DIMENSIONS_JS: str = files("weld.web").joinpath("syncDimensions.js").read_text()
INPUT_MASK_JS: str = files("weld.web").joinpath("inputMask.js").read_text()
WELD_BIND: str = os.path.join(XDG_CONFIG_HOME, "hypr", "weld.conf")


__all__ = [
    "XDG_CONFIG_HOME",
    "WIDGET_DIR",
    "SOCKET_PATH",
    "TEXT_ENCODING",
    "SOURCE_HTML",
    "SCRIPT_MESSAGE_HANDLER",
    "SCRIPT_MESSAGE_RECEIVED_SIGNAL",
    "WELD_BIND",
]
