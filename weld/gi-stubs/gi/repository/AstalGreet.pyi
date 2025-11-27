from typing import Any, Callable, List, Optional, Type

from gi.repository import Gio, GObject

MAJOR_VERSION: int
MINOR_VERSION: int
MICRO_VERSION: int
VERSION: str

class ErrorType(GObject.GEnum):
    AUTH_ERROR = 0
    ERROR = 1

class AuthMessageType(GObject.GEnum):
    VISIBLE = 0
    SECRET = 1
    INFO = 2
    ERROR = 3

class Response(GObject.Object):
    """
    Base Response type.
    """

    pass

class Success(Response):
    """
    Indicates that the request succeeded.
    """

    pass

class Error(Response):
    """
    Indicates that the request succeeded (with an error state).
    """

    def get_error_type(self) -> ErrorType: ...
    def get_description(self) -> str: ...
    @property
    def error_type(self) -> ErrorType: ...
    @error_type.setter
    def error_type(self, value: ErrorType) -> None: ...
    @property
    def description(self) -> str: ...
    @description.setter
    def description(self, value: str) -> None: ...

class AuthMessage(Response):
    """
    Indicates that the request succeeded (with an auth message).
    """

    def get_message_type(self) -> AuthMessageType: ...
    def get_message(self) -> str: ...
    @property
    def message_type(self) -> AuthMessageType: ...
    @message_type.setter
    def message_type(self, value: AuthMessageType) -> None: ...
    @property
    def message(self) -> str: ...
    @message.setter
    def message(self, value: str) -> None: ...

class Request(GObject.Object):
    """
    Base Request type.
    """

    def send(
        self,
        callback: Optional[
            Callable[[GObject.Object, Gio.AsyncResult, Any], None]
        ] = None,
        user_data: Any = None,
    ) -> None: ...
    def send_finish(self, res: Gio.AsyncResult) -> Response: ...
    def get_type_name(self) -> str: ...
    @property
    def type_name(self) -> str: ...

class CreateSession(Request):
    """
    Creates a session and initiates a login attempt for the given user.
    """

    @classmethod
    def new(cls, username: str) -> CreateSession: ...
    def get_username(self) -> str: ...
    def set_username(self, value: str) -> None: ...
    @property
    def username(self) -> str: ...
    @username.setter
    def username(self, value: str) -> None: ...

class PostAuthMesssage(Request):
    """
    Answers an authentication message.
    """

    @classmethod
    def new(cls, response: str) -> PostAuthMesssage: ...
    def get_response(self) -> str: ...
    def set_response(self, value: str) -> None: ...
    @property
    def response(self) -> str: ...
    @response.setter
    def response(self, value: str) -> None: ...

class StartSession(Request):
    """
    Requests for the session to be started using the provided command line.
    """

    @classmethod
    def new(cls, cmd: List[str], env: List[str]) -> StartSession: ...
    def get_cmd(self) -> List[str]: ...
    def set_cmd(self, value: List[str]) -> None: ...
    def get_env(self) -> List[str]: ...
    def set_env(self, value: List[str]) -> None: ...
    @property
    def cmd(self) -> List[str]: ...
    @cmd.setter
    def cmd(self, value: List[str]) -> None: ...
    @property
    def env(self) -> List[str]: ...
    @env.setter
    def env(self, value: List[str]) -> None: ...

class CancelSession(Request):
    """
    Cancels the session that is currently under configuration.
    """

    @classmethod
    def new(cls) -> CancelSession: ...

def login(
    username: str,
    password: str,
    cmd: str,
    callback: Optional[Callable[[GObject.Object, Gio.AsyncResult, Any], None]] = None,
    user_data: Any = None,
) -> None: ...
def login_finish(res: Gio.AsyncResult) -> None: ...
def login_with_env(
    username: str,
    password: str,
    cmd: str,
    env: List[str],
    callback: Optional[Callable[[GObject.Object, Gio.AsyncResult, Any], None]] = None,
    user_data: Any = None,
) -> None: ...
def login_with_env_finish(res: Gio.AsyncResult) -> None: ...
