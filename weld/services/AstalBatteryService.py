# BATTERY SERVICE (using Astal/Battery)
import json
import math
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    NotRequired,
    Set,
    Tuple,
    TypedDict,
)

import gi

from ..gi_modules import GLib
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalBattery", "0.1")
from gi.repository import AstalBattery

BatteryPropertyKey = Literal[
    "present",
    "icon",
    "percentage",
    "charging",
    "timeToEmpty",
    "timeToFull",
    "energy",
    "energyFull",
    "energyRate",
    "state",
]


class BatteryServiceArgs(TypedDict):
    """
    Configuration options for the AstalBatteryService.
    - thingsToWatch: A list of properties to actively monitor.
                     Omitting this means no signals will be connected.
    """

    thingsToWatch: NotRequired[List[BatteryPropertyKey]]


PROPERTY_MAP: Dict[
    BatteryPropertyKey, Tuple[str, Callable[[AstalBattery.Device], Any]]
] = {
    "present": ("is-present", lambda bat: bat.get_is_present()),
    "icon": ("battery-icon-name", lambda bat: bat.get_battery_icon_name()),
    "percentage": ("percentage", lambda bat: math.floor(bat.get_percentage() * 100)),
    "charging": ("charging", lambda bat: bat.get_charging()),
    "timeToEmpty": ("time-to-empty", lambda bat: bat.get_time_to_empty()),
    "timeToFull": ("time-to-full", lambda bat: bat.get_time_to_full()),
    "energy": ("energy", lambda bat: bat.get_energy()),
    "energyFull": ("energy-full", lambda bat: bat.get_energy_full()),
    "energyRate": ("energy-rate", lambda bat: bat.get_energy_rate()),
    "state": ("state", lambda bat: bat.get_state().name),
    # "state": (
    #     "state",
    #     lambda bat: bat.get_state().value_name,
    # ),  # .value_name turns enum to string
}

ALL_PROPERTY_KEYS: Set[BatteryPropertyKey] = set(PROPERTY_MAP.keys())


class AstalBatteryService(WeLDService):
    """
    Service to monitor battery status using AstalBattery.
    This service is configurable to only listen for properties
    specified in the `arguments` dictionary for efficiency.
    """

    def __init__(self, setState: Callable[[str], None], arguments: BatteryServiceArgs):
        """Initialize the AstalBatteryService."""
        super().__init__(setState)

        self.bat = AstalBattery.get_default()
        if not self.bat:
            log_error(
                "Failed to get AstalBattery.Device.get_default(). Service will not run."
            )
            self.watched_keys: List[BatteryPropertyKey] = []
            return

        self.signal_ids = []

        self.watched_keys: List[BatteryPropertyKey] = []
        requested_keys = arguments.get("thingsToWatch", [])

        for key in requested_keys:
            if key in ALL_PROPERTY_KEYS:
                self.watched_keys.append(key)
            else:
                log_error(
                    f"AstalBatteryService: Unknown property key '{key}' in arguments. Ignoring."
                )

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        """
        Start the AstalBatteryService.
        Connects signals ONLY for properties in `self.watched_keys`.
        """

        if not self.bat:
            log_info("AstalBatteryService not starting, battery device not found.")
            return (lambda: None, {})

        log_info(f"Starting AstalBatteryService, watching: {self.watched_keys}")

        if not self.watched_keys:
            log_info(
                "AstalBatteryService: No properties to watch. Service will be idle."
            )

        for key in self.watched_keys:
            gobject_prop, _ = PROPERTY_MAP[key]

            try:
                sid = self.bat.connect(
                    f"notify::{gobject_prop}", self._sync_state_from_signal
                )
                self.signal_ids.append(sid)
            except TypeError:
                log_error(
                    f"Could not connect to 'notify::{gobject_prop}' signal. Typo or property not supported?"
                )

        GLib.idle_add(self._sync_state, False)

        handlers = {"AstalBattery:sync": self._js_sync_request}

        return (self._stop, handlers)

    def _stop(self):
        """Stop the AstalBatteryService and disconnect signals."""
        log_info("Stopping AstalBatteryService...")
        if not self.bat:
            return

        for sid in self.signal_ids:
            try:
                self.bat.disconnect(sid)
            except Exception as e:
                log_error(f"Error disconnecting signal {sid}: {e}")
        self.signal_ids.clear()

    def _js_sync_request(self, data: dict):
        """
        Handle a sync request from the frontend.
        We force a poll of ALL properties on a manual sync.
        """
        if not self.bat:
            return
        log_info("Battery sync requested by frontend (forcing all properties).")
        self._sync_state(force_all=True)

    def _sync_state_from_signal(self, *args):
        """Called by GObject signals. Only syncs *watched* properties."""
        if not self.bat:
            return
        self._sync_state(force_all=False)

    def _sync_state(self, force_all: bool = False, *args):
        """
        Gathers battery properties and sends the state to the frontend.
        - If `force_all` is True, fetches all properties.
        - If `force_all` is False, fetches ONLY watched properties.
        """
        if not self.bat:
            return

        keys_to_fetch = ALL_PROPERTY_KEYS if force_all else self.watched_keys

        if not keys_to_fetch:
            return

        state_dict = {}
        for key in keys_to_fetch:
            try:
                _, getter = PROPERTY_MAP[key]
                state_dict[key] = getter(self.bat)
            except Exception as e:
                log_error(f"Error getting battery property '{key}': {e}")
                state_dict[key] = None

        try:
            state_string = json.dumps(state_dict)
            self._setState(state_string)
        except Exception as e:
            log_error(f"Failed to serialize battery state: {e}")


__all__ = ["AstalBatteryService", "BatteryServiceArgs"]
