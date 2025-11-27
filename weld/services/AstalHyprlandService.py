# HYPRLAND SERVICE (using Astal/Hyprland)
import json
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    NotRequired,
    Optional,
    Set,
    Tuple,
    TypedDict,
)

import gi

from ..gi_modules import GLib
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalHyprland", "0.1")
from gi.repository import AstalHyprland

HyprlandPropertyKey = Literal[
    "monitors",
    "workspaces",
    "clients",
    "focusedClient",
    "focusedMonitor",
    "focusedWorkspace",
    "binds",
    "cursorPosition",
]


class HyprlandServiceArgs(TypedDict):
    """
    Configuration options for the AstalHyprlandService.
    - thingsToWatch: A list of properties to actively monitor.
    """

    thingsToWatch: NotRequired[List[HyprlandPropertyKey]]


def serialize_workspace(ws: AstalHyprland.Workspace | None) -> Dict[str, Any] | None:
    if not ws:
        return None
    return {
        "id": ws.get_id(),
        "name": ws.get_name(),
        "monitor_id": ws.get_monitor().get_id() if ws.get_monitor() else None,
        "has_fullscreen": ws.get_has_fullscreen(),
        "clients_count": len(ws.get_clients() or []),
    }


def serialize_client(client: AstalHyprland.Client | None) -> Dict[str, Any] | None:
    if not client:
        return None
    return {
        "address": client.get_address(),
        "title": client.get_title(),
        "class": client.get_class(),
        "initial_class": client.get_initial_class(),
        "pid": client.get_pid(),
        "x": client.get_x(),
        "y": client.get_y(),
        "width": client.get_width(),
        "height": client.get_height(),
        "floating": client.get_floating(),
        "fullscreen": client.get_fullscreen() == AstalHyprland.Fullscreen.FULLSCREEN,
        "workspace_id": (
            client.get_workspace().get_id() if client.get_workspace() else None
        ),
        "monitor_id": client.get_monitor().get_id() if client.get_monitor() else None,
    }


def serialize_monitor(mon: AstalHyprland.Monitor | None) -> Dict[str, Any] | None:
    if not mon:
        return None
    return {
        "id": mon.get_id(),
        "name": mon.get_name(),
        "model": mon.get_model(),
        "width": mon.get_width(),
        "height": mon.get_height(),
        "refresh_rate": mon.get_refresh_rate(),
        "scale": mon.get_scale(),
        "x": mon.get_x(),
        "y": mon.get_y(),
        "active_workspace_id": (
            mon.get_active_workspace().get_id() if mon.get_active_workspace() else None
        ),
        "focused": mon.get_focused(),
    }


def serialize_bind(bind: AstalHyprland.Bind) -> Dict[str, Any]:
    return {
        "key": bind.get_key(),
        "modmask": bind.get_modmask(),
        "dispatcher": bind.get_dispatcher(),
        "arg": bind.get_arg(),
        "description": bind.get_description(),
    }


PROPERTY_MAP: Dict[
    HyprlandPropertyKey, Tuple[str, Callable[[AstalHyprland.Hyprland], Any]]
] = {
    "monitors": (
        "monitors",
        lambda h: [serialize_monitor(m) for m in (h.get_monitors() or [])],
    ),
    "workspaces": (
        "workspaces",
        lambda h: [serialize_workspace(w) for w in (h.get_workspaces() or [])],
    ),
    "clients": (
        "clients",
        lambda h: [serialize_client(c) for c in (h.get_clients() or [])],
    ),
    "focusedClient": (
        "focused-client",
        lambda h: serialize_client(h.get_focused_client()),
    ),
    "focusedMonitor": (
        "focused-monitor",
        lambda h: serialize_monitor(h.get_focused_monitor()),
    ),
    "focusedWorkspace": (
        "focused-workspace",
        lambda h: serialize_workspace(h.get_focused_workspace()),
    ),
    "binds": ("binds", lambda h: [serialize_bind(b) for b in (h.get_binds() or [])]),
    "cursorPosition": (
        "cursor-position",
        lambda h: (
            {"x": h.get_cursor_position().get_x(), "y": h.get_cursor_position().get_y()}
            if h.get_cursor_position()
            else {"x": 0, "y": 0}
        ),
    ),
}

ALL_PROPERTY_KEYS: Set[HyprlandPropertyKey] = set(PROPERTY_MAP.keys())

EXTRA_SIGNALS: Dict[HyprlandPropertyKey, List[str]] = {
    "clients": ["client-added", "client-removed", "client-moved"],
    "workspaces": ["workspace-added", "workspace-removed"],
    "monitors": ["monitor-added", "monitor-removed"],
}


class AstalHyprlandService(WeLDService):
    """
    Service to monitor Hyprland status using AstalHyprland.
    """

    def __init__(self, setState: Callable[[str], None], arguments: HyprlandServiceArgs):
        """Initialize the AstalHyprlandService."""
        super().__init__(setState)

        self.hypr = AstalHyprland.get_default()
        if not self.hypr:
            log_error(
                "Failed to get AstalHyprland.Hyprland.get_default(). Service will not run."
            )
            self.watched_keys: List[HyprlandPropertyKey] = []
            return

        self.signal_ids = []
        self.watched_keys: List[HyprlandPropertyKey] = []
        requested_keys = arguments.get("thingsToWatch", [])

        for key in requested_keys:
            if key in ALL_PROPERTY_KEYS:
                self.watched_keys.append(key)
            else:
                log_error(
                    f"AstalHyprlandService: Unknown property key '{key}' in arguments. Ignoring."
                )

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        if not self.hypr:
            return (lambda: None, {})

        log_info(f"Starting AstalHyprlandService, watching: {self.watched_keys}")

        # CONNECT SIGNALS
        for key in self.watched_keys:
            gobject_prop, _ = PROPERTY_MAP[key]

            should_notify = key not in ["clients", "workspaces", "monitors"]

            if should_notify:
                try:
                    sid = self.hypr.connect(
                        f"notify::{gobject_prop}", self._sync_state_from_signal
                    )
                    self.signal_ids.append(sid)
                except TypeError:
                    log_error(f"Could not connect to 'notify::{gobject_prop}'.")

            if key in EXTRA_SIGNALS:
                for sig_name in EXTRA_SIGNALS[key]:
                    try:
                        sid = self.hypr.connect(sig_name, self._sync_state_from_signal)
                        self.signal_ids.append(sid)
                    except Exception as e:
                        log_error(
                            f"Failed to connect extra signal '{sig_name}' for key '{key}': {e}"
                        )

        # Initial Sync
        GLib.idle_add(self._sync_state, False)

        handlers = {
            "AstalHyprland:sync": self._js_sync_request,
            "AstalHyprland:dispatch": self._js_dispatch_request,
        }

        return (self._stop, handlers)

    def _stop(self):
        log_info("Stopping AstalHyprlandService...")
        if not self.hypr:
            return
        for sid in self.signal_ids:
            try:
                self.hypr.disconnect(sid)
            except Exception:
                pass
        self.signal_ids.clear()

    def _js_sync_request(self, data: dict):
        self._sync_state(force_all=True)

    def _js_dispatch_request(self, data: dict):
        if not self.hypr:
            return
        dispatcher = data.get("dispatcher")
        arg = data.get("arg", "")
        if dispatcher:
            self.hypr.dispatch(dispatcher, arg)

    def _sync_state_from_signal(self, *args):
        if not self.hypr:
            return
        GLib.timeout_add(50, self._sync_state, False)

    def _sync_state(self, force_all: bool = False, *args):
        """Gather properties and send state."""
        if not self.hypr:
            return False

        keys_to_fetch = ALL_PROPERTY_KEYS if force_all else self.watched_keys
        state_dict = {}

        for key in keys_to_fetch:
            try:
                if key == "focusedClient":
                    try:
                        client = self.hypr.get_focused_client()
                        state_dict[key] = serialize_client(client)
                    except Exception as e:
                        log_error(
                            f"Safety Catch: Could not serialize focusedClient (Zombie object?): {e}"
                        )
                        state_dict[key] = None
                else:
                    _, getter = PROPERTY_MAP[key]
                    state_dict[key] = getter(self.hypr)

            except Exception as e:
                log_error(f"Error getting Hyprland property '{key}': {e}")
                state_dict[key] = None

        try:
            state_string = json.dumps(state_dict)
            self._setState(state_string)
        except Exception as e:
            log_error(f"Failed to serialize Hyprland state: {e}")

        return False


__all__ = ["AstalHyprlandService", "HyprlandServiceArgs"]
