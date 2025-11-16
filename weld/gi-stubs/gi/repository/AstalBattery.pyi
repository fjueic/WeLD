# Stubs generated from AstalBattery-0.1.gir
import enum
from typing import Any, Callable, List, Optional

from gi.repository import GLib, GObject

class State(enum.IntEnum):
    UNKNOWN = 0
    CHARGING = 1
    DISCHARGING = 2
    EMPTY = 3
    FULLY_CHARGED = 4
    PENDING_CHARGE = 5
    PENDING_DISCHARGE = 6

class Technology(enum.IntEnum):
    UNKNOWN = 0
    LITHIUM_ION = 1
    LITHIUM_POLYMER = 2
    LITHIUM_IRON_PHOSPHATE = 3
    LEAD_ACID = 4
    NICKEL_CADMIUM = 5
    NICKEL_METAL_HYDRIDE = 6

class WarningLevel(enum.IntEnum):
    UNKNOWN = 0
    NONE = 1
    DISCHARGING = 2
    LOW = 3
    CRITICIAL = 4
    ACTION = 5

class BatteryLevel(enum.IntEnum):
    UNKNOWN = 0
    NONE = 1
    LOW = 2
    CRITICIAL = 3
    NORMAL = 4
    HIGH = 5
    FULL = 6

class Type(enum.IntEnum):
    UNKNOWN = 0
    LINE_POWER = 1
    BATTERY = 2
    UPS = 3
    MONITOR = 4
    MOUSE = 5
    KEYBOARD = 6
    PDA = 7
    PHONE = 8
    MEDIA_PLAYER = 9
    TABLET = 10
    COMPUTER = 11
    GAMING_INPUT = 12
    PEN = 13
    TOUCHPAD = 14
    MODEM = 15
    NETWORK = 16
    HEADSET = 17
    SPEAKERS = 18
    HEADPHONES = 19
    VIDEO = 20
    OTHER_AUDIO = 21
    REMOVE_CONTROL = 22
    PRINTER = 23
    SCANNER = 24
    CAMERA = 25
    WEARABLE = 26
    TOY = 27
    BLUETOOTH_GENERIC = 28

class Device(GObject.Object):
    # Properties
    device_type: GObject.Property[Type, Any]
    native_path: GObject.Property[str, Any]
    vendor: GObject.Property[str, Any]
    model: GObject.Property[str, Any]
    serial: GObject.Property[str, Any]
    update_time: GObject.Property[int, Any]
    power_supply: GObject.Property[bool, Any]
    online: GObject.Property[bool, Any]
    energy: GObject.Property[float, Any]
    energy_empty: GObject.Property[float, Any]
    energy_full: GObject.Property[float, Any]
    energy_full_design: GObject.Property[float, Any]
    energy_rate: GObject.Property[float, Any]
    voltage: GObject.Property[float, Any]
    charge_cycles: GObject.Property[int, Any]
    luminosity: GObject.Property[float, Any]
    time_to_empty: GObject.Property[int, Any]
    time_to_full: GObject.Property[int, Any]
    percentage: GObject.Property[float, Any]
    temperature: GObject.Property[float, Any]
    is_present: GObject.Property[bool, Any]
    state: GObject.Property[State, Any]
    is_rechargable: GObject.Property[bool, Any]
    capacity: GObject.Property[float, Any]
    technology: GObject.Property[Technology, Any]
    warning_level: GObject.Property[WarningLevel, Any]
    battery_level: GObject.Property[BatteryLevel, Any]
    icon_name: GObject.Property[str, Any]
    charging: GObject.Property[bool, Any]
    is_battery: GObject.Property[bool, Any]
    battery_icon_name: GObject.Property[str, Any]
    device_type_name: GObject.Property[str, Any]
    device_type_icon: GObject.Property[str, Any]

    # Static Methods & Constructors
    @staticmethod
    def get_default() -> Optional[Device]: ...
    def new(path: GLib.ObjectPath) -> Device: ...

    # Methods
    def get_device_type(self) -> Type: ...
    def get_native_path(self) -> str: ...
    def get_vendor(self) -> str: ...
    def get_model(self) -> str: ...
    def get_serial(self) -> str: ...
    def get_update_time(self) -> int: ...
    def get_power_supply(self) -> bool: ...
    def get_online(self) -> bool: ...
    def get_energy(self) -> float: ...
    def get_energy_empty(self) -> float: ...
    def get_energy_full(self) -> float: ...
    def get_energy_full_design(self) -> float: ...
    def get_energy_rate(self) -> float: ...
    def get_voltage(self) -> float: ...
    def get_charge_cycles(self) -> int: ...
    def get_luminosity(self) -> float: ...
    def get_time_to_empty(self) -> int: ...
    def get_time_to_full(self) -> int: ...
    def get_percentage(self) -> float: ...
    def get_temperature(self) -> float: ...
    def get_is_present(self) -> bool: ...
    def get_state(self) -> State: ...
    def get_is_rechargable(self) -> bool: ...
    def get_capacity(self) -> float: ...
    def get_technology(self) -> Technology: ...
    def get_warning_level(self) -> WarningLevel: ...
    def get_battery_level(self) -> BatteryLevel: ...
    def get_icon_name(self) -> str: ...
    def get_charging(self) -> bool: ...
    def get_is_battery(self) -> bool: ...
    def get_battery_icon_name(self) -> str: ...
    def get_device_type_name(self) -> str: ...
    def get_device_type_icon(self) -> str: ...

class UPower(GObject.Object):
    # Properties
    devices: GObject.Property[GLib.List[Device], Any]
    display_device: GObject.Property[Device, Any]
    daemon_version: GObject.Property[str, Any]
    on_battery: GObject.Property[bool, Any]
    lid_is_closed: GObject.Property[bool, Any]
    lid_is_present: GObject.Property[bool, Any]
    critical_action: GObject.Property[str, Any]

    # Constructor
    def new(self) -> UPower: ...

    # Methods
    def get_devices(self) -> GLib.List[Device]: ...
    def get_display_device(self) -> Device: ...
    def get_daemon_version(self) -> str: ...
    def get_on_battery(self) -> bool: ...
    def get_lid_is_closed(self) -> bool: ...
    def get_lid_is_present(self) -> bool: ...
    def get_critical_action(self) -> str: ...

    # Signals
    def connect(self, signal: str, callback: Callable, *args: Any) -> int:
        if signal == "device-added":
            ...  # callback(self, device: Device)
        elif signal == "device-removed":
            ...  # callback(self, device: Device)
        else:
            ...  # Fallback for parent signals

# Top-level namespace functions
def get_default() -> Device: ...

# --- Top-level Constants ---
MAJOR_VERSION: int
MINOR_VERSION: int
MICRO_VERSION: int
VERSION: str
