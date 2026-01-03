from weld.services.AstalMprisService import AstalMprisService
from weld.type import UpdateStrategy

config = {
    "title": "mpris-player",
    "layer": "overlay",
    "anchors": ["top", "right"],
    "width": 400,
    "height": 550,
    "focus": "on_demand",
    "transparency": True,
    "devTool": 1,
    "allowedRoutes": ["/"],
}

states = [
    {
        "event": "mpris",
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": AstalMprisService,
        "service_arguments": {},  # No args needed
    }
]
