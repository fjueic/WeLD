from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Tuple


class WeLDService(ABC):
    """
    Abstract Base Class for a WeLD background service.

    This provides a pattern for running persistent Python logic inside WeLD.

    I'm going to hate writing wrapper for all these =(
    """

    def __init__(self, setState: Callable[[str], None]):
        """
        Called by WidgetWindow.

        :param setState: The thread-safe B->F (Python to JS) function.
                         Call this from any thread to send data to the frontend.
                         Use this to update the widget state(s).
        :param arguments: Additional arguments for user-defined things.
        """

        self._setState = setState
        self._manual_handlers: Dict[str, Callable] = {}

    @abstractmethod
    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        """
        Called by WidgetWindow to start the service.

        - This method MUST be non-blocking.
        - Start all background threads or GLib listeners here.

        :returns: A tuple containing:
                  (stop_function, handlers_dict)
        """
        pass


__all__ = ["WeLDService"]
