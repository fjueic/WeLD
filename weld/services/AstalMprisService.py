import json
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict

import gi

from ..gi_modules import GLib
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalMpris", "0.1")
from gi.repository import AstalMpris


class MprisServiceArgs(TypedDict):
    pass


def serialize_player(player: AstalMpris.Player) -> Dict[str, Any]:
    """Converts a Player object into a JSON-friendly dict."""
    if not player:
        return {}

    try:
        # Map Enums to Strings for JSON
        status_map = {
            AstalMpris.PlaybackStatus.PLAYING: "Playing",
            AstalMpris.PlaybackStatus.PAUSED: "Paused",
            AstalMpris.PlaybackStatus.STOPPED: "Stopped",
        }

        loop_map = {
            AstalMpris.Loop.UNSUPPORTED: "Unsupported",
            AstalMpris.Loop.NONE: "None",
            AstalMpris.Loop.TRACK: "Track",
            AstalMpris.Loop.PLAYLIST: "Playlist",
        }

        shuffle_map = {
            AstalMpris.Shuffle.UNSUPPORTED: "Unsupported",
            AstalMpris.Shuffle.ON: "On",
            AstalMpris.Shuffle.OFF: "Off",
        }

        return {
            "bus_name": player.get_bus_name(),
            "identity": player.get_identity(),
            "entry": player.get_entry(),
            "title": player.get_title(),
            "artist": player.get_artist(),
            "album": player.get_album(),
            "art_url": player.get_art_url(),
            "cover_art": player.get_cover_art(),
            "length": player.get_length(),
            "rate": player.get_rate(),
            "position": player.get_position(),
            "volume": player.get_volume(),
            "playback_status": status_map.get(player.get_playback_status(), "Unknown"),
            "loop_status": loop_map.get(player.get_loop_status(), "None"),
            "shuffle_status": shuffle_map.get(player.get_shuffle_status(), "Off"),
            "can_go_next": player.get_can_go_next(),
            "can_go_prev": player.get_can_go_previous(),
            "can_play": player.get_can_play(),
            "can_pause": player.get_can_pause(),
        }
    except Exception as e:
        log_error(f"Error serializing player: {e}")
        return {}


class AstalMprisService(WeLDService):
    def __init__(self, setState: Callable[[str], None], arguments: MprisServiceArgs):
        super().__init__(setState)
        self.first_run = True
        self.mpris: AstalMpris.Mpris = None  # type: ignore
        self.player_signals: Dict[str, List[int]] = {}
        self.players_map: Dict[str, AstalMpris.Player] = {}

        if AstalMpris:
            try:
                self.mpris = AstalMpris.Mpris.get_default()
            except Exception as e:
                log_error(f"Failed to get AstalMpris default: {e}")

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        # if not self.mpris:
        #     return (lambda: None, {})

        log_info("Starting AstalMprisService...")

        self.mpris.connect("player-added", self._on_player_added)
        self.mpris.connect("player-closed", self._on_player_closed)
        for player in self.mpris.get_players():
            self._on_player_added(self.mpris, player)

        handlers = {
            "Astalmpris:play_pause": self._handle_play_pause,
            "Astalmpris:next": self._handle_next,
            "Astalmpris:prev": self._handle_prev,
            "Astalmpris:sync": self._handle_sync,
            "Astalmpris:set_position": self._handle_set_position,
            "Astalmpris:set_volume": self._handle_set_volume,
            "Astalmpris:shuffle": self._handle_shuffle,
            "Astalmpris:loop": self._handle_loop,
        }

        GLib.idle_add(self._push_state)
        return (self._stop, handlers)

    def _handle_set_volume(self, data: dict):
        """
        Sets the volume of the specified player.
        Expects 'volume' to be a float between 0.0 and 1.0.
        """
        p = self._get_player(data)
        val = data.get("volume")

        if p and val is not None:
            try:
                vol_float = max(0.0, min(1.0, float(val)))
                p.set_volume(vol_float)
                self._push_state()
            except Exception as e:
                log_error(f"Failed to set volume: {e}")

    def _handle_shuffle(self, data: dict):
        """
        Toggles shuffle status.
        """
        p = self._get_player(data)
        if p:
            try:
                p.shuffle()
                self._push_state()
            except Exception as e:
                log_error(f"Failed to toggle shuffle: {e}")

    def _handle_loop(self, data: dict):
        """
        Cycles loop status
        """
        p = self._get_player(data)
        if p:
            try:
                p.loop()
                self._push_state()
            except Exception as e:
                log_error(f"Failed to cycle loop: {e}")

    def _handle_set_position(self, data: dict):
        p = self._get_player(data)
        pos = data.get("position")
        if p and pos is not None:
            p.set_position(float(pos))

    def _stop(self):
        log_info("Stopping AstalMprisService...")
        # Clean up signals
        for bus_name, signals in self.player_signals.items():
            player = self.players_map.get(bus_name)
            if player:
                for sig_id in signals:
                    try:
                        player.disconnect(sig_id)
                    except:
                        pass
        self.player_signals.clear()
        self.players_map.clear()

    def _on_player_added(self, _, player: AstalMpris.Player):
        bus_name = player.get_bus_name()
        if bus_name in self.players_map:
            return

        self.players_map[bus_name] = player
        self.player_signals[bus_name] = []

        props = [
            "playback-status",
            "title",
            "artist",
            "cover-art",
            "volume",
            "can-go-next",
            "can-go-previous",
            "rate",
            "position",
            "metadata",
        ]

        for prop in props:
            try:
                sid = player.connect(f"notify::{prop}", self._on_player_change)
                self.player_signals[bus_name].append(sid)
            except Exception:
                pass

        self._push_state()

    def _on_player_closed(self, _, player: AstalMpris.Player):
        bus_name = player.get_bus_name()

        if bus_name in self.player_signals:
            self.player_signals.pop(bus_name)

        if bus_name in self.players_map:
            self.players_map.pop(bus_name)

        self._push_state()

    def _on_player_change(self, *args):
        self._push_state()

    def _push_state(self):
        players_list = []
        for p in self.players_map.values():
            if p.get_available():
                players_list.append(serialize_player(p))

        try:
            self._setState(json.dumps({"players": players_list}))
        except Exception:
            pass

    def _get_player(self, data: dict) -> Optional[AstalMpris.Player]:
        """Find player by bus_name or default to first."""
        name = data.get("bus_name")
        if name and name in self.players_map:
            return self.players_map[name]
        if self.players_map:
            return next(iter(self.players_map.values()))
        return None

    def _handle_play_pause(self, data: dict):
        p = self._get_player(data)
        if p:
            p.play_pause()

    def _handle_next(self, data: dict):
        p = self._get_player(data)
        if p:
            p.next()

    def _handle_prev(self, data: dict):
        p = self._get_player(data)
        if p:
            p.previous()

    def _handle_sync(self, data: dict):
        self._push_state()


__all__ = ["AstalMprisService", "MprisServiceArgs"]
