from weld.services.AstalAuthService import AstalAuthService
from weld.type import UpdateStrategy

config = {
    "title": "auth-widget",
    "layer": "overlay",
    "anchors": ["top"],
    "width": 300,
    "height": 250,
    "focus": "on_demand",
    "transparency": True,
    # "syncDimension": True,
}

states = [
    {
        "event": "auth",  # JS listens for "weld:auth"
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": AstalAuthService,
        "service_arguments": {
            # "polkit-1" is standard for desktop auth.
            "service": "polkit-1",
        },
    }
]
