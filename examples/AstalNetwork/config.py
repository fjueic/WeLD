from weld.services.AstalNetworkService import AstalNetworkService
from weld.type import UpdateStrategy

config = {
    "title": "astal-network",
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
        "event": "network",
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": AstalNetworkService,
        "service_arguments": {},  # No args needed
    }
]
