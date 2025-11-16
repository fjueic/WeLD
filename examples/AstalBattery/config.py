# Import the service class from your WeLD project
# import will also work when this is in ~/.config/weld/ though lsp might not resolve it
from weld.services.AstalBatteryService import AstalBatteryService
from weld.type import UpdateStrategy

# List of all available keys from AstalBatteryService service implementation
ALL_BATTERY_KEYS = [
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

config = {
    "title": "battery-widget",
    "layer": "top",
    "anchors": ["top", "right"],
    "top": 10,
    "right": 10,
    # "width": 300,
    # "height": 280,
    "focus": "none",
    "transparency": True,
    "syncDimension": True,
}

states = [
    {
        "event": "battery",
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": AstalBatteryService,
        "service_arguments": {"thingsToWatch": ALL_BATTERY_KEYS},
    }
]
