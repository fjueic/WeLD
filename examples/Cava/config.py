from weld.services.CavaService import CavaService
from weld.type import UpdateStrategy

config = {
    "title": "cava-visualizer",
    "layer": "overlay",
    "anchors": ["bottom", "right"],
    "width": 600,
    "height": 200,
    "focus": "on_demand",
    "transparency": True,
    "syncDimension": True,
    "devTool": True,
}

states = [
    {
        "event": "cava",
        "updateStrategy": UpdateStrategy.SERVICE,
        "service_factory": CavaService,
        "service_arguments": {
            "bars": 32,
            "framerate": 20,
            "autosens": True,
            "low_cutoff": 50,
            "high_cutoff": 10000,
            "stereo": False,
            "channels": 1,
            "samplerate": 44100,
            "source": "auto",
            # "noise_reduction": 0.2,
        },
    }
]
