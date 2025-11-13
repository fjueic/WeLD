##############################################################################
############## ONLY FOR TESTING PURPOSES #####################################
############## WILL BE REPLACED WITH PROPER BATTERY SERVICE ##################
##############################################################################
import json
import math
from typing import Any, Callable, Dict, Tuple

from ..gi_modules import AstalBattery, GLib
from ..log import log_info
from .base import WeLDService


class AstalBatteryService(WeLDService):
    def __init__(self, setState: Callable[[str], None]):
        super().__init__(setState)
        self.bat = AstalBattery.get_default()
        self.signal_ids = []

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        log_info("Starting AstalBatteryService...")

        self.signal_ids.append(self.bat.connect("notify::is-present", self._sync_state))
        self.signal_ids.append(
            self.bat.connect("notify::battery-icon-name", self._sync_state)
        )
        self.signal_ids.append(self.bat.connect("notify::percentage", self._sync_state))

        # Send initial state right away
        GLib.idle_add(self._sync_state)

        # Define handlers for JS to call
        handlers = {"battery:sync": self._js_sync_request}

        # Return the stop function and the handlers
        return (self._stop, handlers)

    def _stop(self):
        log_info("Stopping AstalBatteryService...")
        for sid in self.signal_ids:
            self.bat.disconnect(sid)
        self.signal_ids.clear()

    def _js_sync_request(self, data: dict):
        log_info("Battery sync requested by frontend.")
        self._sync_state()

    def _sync_state(self, *args):
        percentage_float = self.bat.get_percentage()

        state_dict = {
            "present": self.bat.get_is_present(),
            "icon": self.bat.get_battery_icon_name(),
            "percentage": math.floor(percentage_float * 100),
        }

        state_string = json.dumps(state_dict)
        self._setState(state_string)
