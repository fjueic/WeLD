from weld.services.AstalTrayService import AstalTrayService
from weld.type import UpdateStrategy

config = {
    "title": "astal-network",
    "layer": "overlay",
    "anchors": ["top", "right"],
    "width": 400,
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
        "service_factory": AstalTrayService,
        "service_arguments": {},  # No args needed
    }
]
