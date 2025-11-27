from weld.services.AstalHyprlandService import AstalHyprlandService
from weld.type import UpdateStrategy

# List of all available keys defined in the AstalHyprlandService
ALL_HYPRLAND_KEYS = [
    "monitors",
    "workspaces",
    "clients", 
    "focusedClient",
    "focusedMonitor",
    "focusedWorkspace",
    "binds",
    "cursorPosition",
]

config = {
    "title": "hyprland-dashboard",
    "layer": "top",
    "anchors": ["top", "left"], 
    "top": 10,
    "left": 10,
    "focus": "on_demand",
    "transparency": True,
    "syncDimension": True,
    "devTool": 1,
}

states = [
    {
        "event": "hyprland",
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": AstalHyprlandService,
        "service_arguments": {"thingsToWatch": ALL_HYPRLAND_KEYS},
    }
]
