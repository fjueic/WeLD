from weld.services.AstalNotifdService import AstalNotifdService
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
        "event": "notifd",
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": AstalNotifdService,
        "service_arguments": {},  # No args needed
    }
]
