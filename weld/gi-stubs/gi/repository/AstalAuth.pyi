# Stubs generated from AstalAuth-0.1.gir
from typing import Any, Callable, Optional

from gi.repository import Gio, GLib, GObject

class Pam(GObject.Object):
    """
    Stub for AstalAuth.Pam.
    """

    # Properties
    service: GObject.Property[str, Any]
    username: GObject.Property[str, Any]

    # Static Methods
    @staticmethod
    def authenticate(
        password: str,
        result_callback: Optional[
            Callable[[GObject.Object, Gio.AsyncResult, Any], None]
        ],
        user_data: Any,
    ) -> bool: ...
    @staticmethod
    def authenticate_finish(res: Gio.AsyncResult) -> int: ...

    # Methods
    def get_service(self) -> str: ...
    def get_username(self) -> str: ...
    def set_service(self, service: str) -> None: ...
    def set_username(self, username: str) -> None: ...
    def start_authenticate(self) -> bool: ...
    def supply_secret(self, secret: Optional[str]) -> None: ...

    # Signals
    def connect(self, signal: str, callback: Callable, *args: Any) -> int:
        if signal == "auth-error":
            ...  # callback(self, msg: str)
        elif signal == "auth-info":
            ...  # callback(self, msg: str)
        elif signal == "auth-prompt-hidden":
            ...  # callback(self, msg: str)
        elif signal == "auth-prompt-visible":
            ...  # callback(self, msg: str)
        elif signal == "fail":
            ...  # callback(self, msg: str)
        elif signal == "success":
            ...  # callback(self)
        else:
            ...  # Fallback for parent signals

# --- Top-level Constants ---

MAJOR_VERSION: int
MICRO_VERSION: int
MINOR_VERSION: int
VERSION: str
