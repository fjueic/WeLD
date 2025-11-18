from weld.services.AstalBluetoothService import AstalBluetoothService
from weld.type import UpdateStrategy

config = {
    "title": "bluetooth-manager",
    "layer": "overlay",
    "anchors": ["top", "right"],
    "top": 10,
    "right": 10,
    "width": 360,
    "height": 600,
    "focus": "on_demand",
    "transparency": True,
}

states = [
    {
        "event": "bluetooth",
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": AstalBluetoothService,
    }
]
