import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import gi

from ..gi_modules import GLib, GObject
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalNetwork", "0.1")
from gi.repository import AstalNetwork


class AstalNetworkService(WeLDService):
    def __init__(self, setState: Callable[[str], None], arguments: dict):
        super().__init__(setState)
        self.nm = None
        self.is_ready = False
        self._signal_ids = []

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        GLib.idle_add(self._do_init)
        return (
            self._stop,
            {
                "AstalNetwork:wifi_scan": self._wifi_scan,
                "AstalNetwork:wifi_toggle": self._wifi_toggle,
                "AstalNetwork:wifi_connect": self._wifi_connect,
                "AstalNetwork:wifi_disconnect": self._wifi_disconnect,
                "AstalNetwork:sync": lambda _: self._push_state(),
            },
        )

    def _do_init(self) -> bool:
        try:
            self.nm = AstalNetwork.get_default()

            # Helper to connect signals
            def watch(obj, prop, cb):
                if obj:
                    sid = obj.connect(f"notify::{prop}", cb)
                    self._signal_ids.append((obj, sid))

            # Main Network Object
            watch(self.nm, "primary", self._on_update)
            watch(self.nm, "connectivity", self._on_update)
            watch(self.nm, "state", self._on_update)

            # Wifi Object
            wifi = self.nm.get_wifi()
            if wifi:
                watch(wifi, "enabled", self._on_update)
                watch(wifi, "active-access-point", self._on_update)
                watch(wifi, "scanning", self._on_update)
                # Specific signals for lists
                self._signal_ids.append(
                    (wifi, wifi.connect("access-point-added", self._on_update))
                )
                self._signal_ids.append(
                    (wifi, wifi.connect("access-point-removed", self._on_update))
                )

            self.is_ready = True
            self._push_state()
        except Exception as e:
            log_error(f"Network Init Failed: {e}")
        return False

    def _on_update(self, *args):
        self._push_state()

    def _push_state(self):
        if not self.nm:
            return False

        try:
            wifi = self.nm.get_wifi()
            wired = self.nm.get_wired()

            # Force refresh if the list is empty but wifi is on
            aps = []
            if wifi and wifi.get_enabled():
                active_ap = wifi.get_active_access_point()
                active_bssid = active_ap.get_bssid() if active_ap else None

                # Iterate the list of AccessPoint GObjects
                raw_aps = wifi.get_access_points()
                for ap in raw_aps or []:
                    ssid = ap.get_ssid()
                    if not ssid:
                        continue

                    aps.append(
                        {
                            "ssid": ssid,
                            "bssid": ap.get_bssid(),
                            "strength": ap.get_strength(),
                            "locked": ap.get_requires_password(),
                            "active": ap.get_bssid() == active_bssid,
                        }
                    )

            data = {
                "primary": int(self.nm.get_primary()),
                "connectivity": int(self.nm.get_connectivity()),
                "state": int(self.nm.get_state()),
                "wifi": (
                    {
                        "enabled": bool(wifi.get_enabled()) if wifi else False,
                        "ssid": wifi.get_ssid() if wifi else "",
                        "strength": wifi.get_strength() if wifi else 0,
                        "scanning": wifi.get_scanning() if wifi else False,
                        "access_points": sorted(
                            aps, key=lambda x: x['strength'], reverse=True
                        ),
                    }
                    if wifi
                    else None
                ),
                "wired": (
                    {"state": int(wired.get_state()), "icon": wired.get_icon_name()}
                    if wired
                    else None
                ),
            }

            self._setState(json.dumps(data))
        except Exception as e:
            log_error(f"Push State Fail: {e}")
        return False

    def _wifi_scan(self, _):
        w = self.nm.get_wifi()
        if w:
            w.scan()

    def _wifi_toggle(self, _):
        w = self.nm.get_wifi()
        if w:
            w.set_enabled(not w.get_enabled())

    def _wifi_connect(self, args):
        w = self.nm.get_wifi()
        if not w:
            return
        for ap in w.get_access_points():
            if ap.get_ssid() == args.get("ssid"):
                # Use password if provided
                ap.activate(args.get("password"), None)
                break

    def _wifi_disconnect(self, _):
        w = self.nm.get_wifi()
        if w:
            w.deactivate_connection(None)

    def _stop(self):
        for obj, sid in self._signal_ids:
            obj.disconnect(sid)
