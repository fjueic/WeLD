from weld.services.TrayService import TrayService
from weld.type import UpdateStrategy

config = {
    "title": "tray",
    "layer": "overlay",
    "anchors": ["bottom", "right"],
    "width": 700,
    "height": 750,
    "focus": "on_demand",
    # "transparency": True,
    "devTool": 1,
    "allowedRoutes": ["/"],
    # "syncDimension": 1,
}

states = [
    {
        "event": "tray",
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": TrayService,
        "service_arguments": {},  # No args needed
    }
]
