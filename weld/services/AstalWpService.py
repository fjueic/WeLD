import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import gi

from ..gi_modules import GLib, GObject
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalWp", "0.1")
from gi.repository import AstalWp


class AstalWpService(WeLDService):
    def __init__(self, setState: Callable[[str], None], arguments: dict):
        super().__init__(setState)
        self.wp: AstalWp.Wp = None
        self._stopped = False
        self._signal_ids: List[Tuple[GObject.Object, int]] = []

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        GLib.idle_add(self._do_init)
        return (
            self._stop,
            {
                "AstalWp:set_volume": self._set_volume,
                "AstalWp:set_mute": self._set_mute,
                "AstalWp:set_default": self._set_default,
                "AstalWp:move_stream": self._move_stream,
                "AstalWp:set_scale": self._set_scale,
                "AstalWp:sync": lambda _: self._push_state(),
            },
        )

    def _connect_safe(self, obj, sig, cb):
        if obj:
            sid = obj.connect(sig, cb)
            self._signal_ids.append((obj, sid))

    def _do_init(self) -> bool:
        try:
            self.wp = AstalWp.Wp.get_default()
            audio = self.wp.get_audio()
            self._connect_safe(self.wp, "ready", self._on_update)

            signals = [
                "speaker-added",
                "speaker-removed",
                "microphone-added",
                "microphone-removed",
                "stream-added",
                "stream-removed",
                "recorder-added",
                "recorder-removed",
            ]
            for sig in signals:
                self._connect_safe(audio, sig, self._on_node_event)

            self._connect_safe(audio, "notify::default-speaker", self._on_update)
            self._connect_safe(audio, "notify::default-microphone", self._on_update)
            self._connect_safe(self.wp, "notify::scale", self._on_update)

            for node in self.wp.get_nodes():
                self._setup_node(node)

            self._push_state()
            log_info("AstalWpService: Audio Service Initialized")
        except Exception as e:
            log_error(f"AstalWp Init Fail: {e}")
        return False

    def _setup_node(self, node):
        self._connect_safe(node, "notify::volume", self._on_update)
        self._connect_safe(node, "notify::mute", self._on_update)
        if hasattr(node, "notify::target-endpoint"):
            self._connect_safe(node, "notify::target-endpoint", self._on_update)

    def _on_node_event(self, audio, node):
        if isinstance(node, AstalWp.Node):
            self._setup_node(node)
        self._push_state()

    def _on_update(self, *args):
        self._push_state()

    def _push_state(self):
        if not self.wp or self._stopped:
            return False
        try:
            audio = self.wp.get_audio()

            def serialize_node(n):
                # Primary name (Application name or hardware description)
                display_name = (
                    n.get_pw_property("application.name")
                    or n.get_description()
                    or n.get_name()
                )

                # Technical info (Node name or path)
                technical_info = n.get_name()

                data = {
                    "id": n.get_id(),
                    "displayName": display_name,
                    "technicalName": technical_info,
                    "volume": n.get_volume(),
                    "mute": n.get_mute(),
                    "state": int(n.get_state()),
                    "isDefault": False,
                }
                if hasattr(n, "get_target_endpoint"):
                    target = n.get_target_endpoint()
                    data["targetId"] = target.get_id() if target else None
                return data

            speakers = [serialize_node(s) for s in audio.get_speakers()]
            mics = [serialize_node(m) for m in audio.get_microphones()]

            def_speaker = audio.get_default_speaker()
            def_mic = audio.get_default_microphone()
            for s in speakers:
                if def_speaker and s["id"] == def_speaker.get_id():
                    s["isDefault"] = True
            for m in mics:
                if def_mic and m["id"] == def_mic.get_id():
                    m["isDefault"] = True

            payload = {
                "scale": int(self.wp.get_scale()),
                "speakers": speakers,
                "microphones": mics,
                "playback": [serialize_node(st) for st in audio.get_streams()],
                "recording": [serialize_node(r) for r in audio.get_recorders()],
            }
            self._setState(json.dumps(payload))
        except Exception as e:
            log_error(f"Wp Push Error: {e}")
        return False

    def _set_volume(self, args):
        n = self.wp.get_node(int(args["id"]))
        if n:
            n.set_volume(float(args["volume"]))

    def _set_mute(self, args):
        n = self.wp.get_node(int(args["id"]))
        if n:
            n.set_mute(bool(args["mute"]))

    def _set_default(self, args):
        n = self.wp.get_node(int(args["id"]))
        if hasattr(n, "set_is_default"):
            n.set_is_default(True)

    def _move_stream(self, args):
        stream = self.wp.get_node(int(args["stream_id"]))
        target = self.wp.get_node(int(args["target_id"]))
        if stream and target and hasattr(stream, "set_target_endpoint"):
            stream.set_target_endpoint(target)

    def _set_scale(self, args):
        self.wp.set_scale(int(args["scale"]))

    def _stop(self):
        self._stopped = True
        for obj, sid in self._signal_ids:
            try:
                if obj.handler_is_connected(sid):
                    obj.disconnect(sid)
            except:
                pass
        self._signal_ids.clear()
        self.wp = None
