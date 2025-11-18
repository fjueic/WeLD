# BLUETOOTH SERVICE 
import json
from typing import Any, Callable, Dict, List, NotRequired, Optional, Tuple, TypedDict

import gi

from ..gi_modules import GLib
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalBluetooth", "0.1")
from gi.repository import AstalBluetooth


class BluetoothServiceArgs(TypedDict):
    pass


class AstalBluetoothService(WeLDService):
    """
    Service to manage Bluetooth using AstalBluetooth.
    Supports Power, Scan, Pair, Trust, Block, Rename, and Connect.
    """

    def __init__(
        self, setState: Callable[[str], None], arguments: BluetoothServiceArgs
    ):
        super().__init__(setState)
        self.arguments = arguments

        self.bt: Optional[AstalBluetooth.Bluetooth] = None
        self.adapter: Optional[AstalBluetooth.Adapter] = None

        self.is_ready = False
        self._stopped = False
        self._signal_ids: List[Tuple[Any, int]] = []

        if AstalBluetooth is None:
            log_error("AstalBluetoothService: Library not found.")

        log_info("AstalBluetoothService: Initialized on worker thread.")

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        if AstalBluetooth is None:
            return (lambda: None, {})

        GLib.idle_add(self._do_init)

        handlers = {
            # --- Adapter Commands ---
            "AstalBluetooth:toggle": self._toggle_power,
            "AstalBluetooth:scan": self._toggle_scan,
            "AstalBluetooth:set_discoverable": self._set_discoverable,
            "AstalBluetooth:set_pairable": self._set_pairable,
            "AstalBluetooth:rename_adapter": self._rename_adapter,
            # --- Device Commands ---
            "AstalBluetooth:connect": self._connect_device,
            "AstalBluetooth:disconnect": self._disconnect_device,
            "AstalBluetooth:pair": self._pair_device,
            "AstalBluetooth:remove_device": self._remove_device,  # Forget
            "AstalBluetooth:trust": self._set_trusted,
            "AstalBluetooth:block": self._set_blocked,
            "AstalBluetooth:rename_device": self._rename_device,
            "AstalBluetooth:sync": self._request_sync,
        }
        return (self._stop, handlers)

    def _stop(self):
        self._stopped = True
        log_info("Stopping AstalBluetoothService...")
        GLib.idle_add(self._do_stop)

    def _dispatch(self, func, *args):
        if self._stopped or not self.is_ready:
            return
        GLib.idle_add(func, *args)

    def _toggle_power(self, args: dict):
        self._dispatch(self._do_toggle_power)

    def _toggle_scan(self, args: dict):
        self._dispatch(self._do_toggle_scan, args.get("scanning", True))

    def _set_discoverable(self, args: dict):
        self._dispatch(self._do_set_discoverable, args.get("val", True))

    def _set_pairable(self, args: dict):
        self._dispatch(self._do_set_pairable, args.get("val", True))

    def _rename_adapter(self, args: dict):
        self._dispatch(self._do_rename_adapter, args.get("name"))

    def _connect_device(self, args: dict):
        self._dispatch(self._do_connect_device, args.get("address"))

    def _disconnect_device(self, args: dict):
        self._dispatch(self._do_disconnect_device, args.get("address"))

    def _pair_device(self, args: dict):
        self._dispatch(self._do_pair_device, args.get("address"))

    def _remove_device(self, args: dict):
        self._dispatch(self._do_remove_device, args.get("address"))

    def _set_trusted(self, args: dict):
        self._dispatch(self._do_set_trusted, args.get("address"), args.get("val", True))

    def _set_blocked(self, args: dict):
        self._dispatch(self._do_set_blocked, args.get("address"), args.get("val", True))

    def _rename_device(self, args: dict):
        self._dispatch(self._do_rename_device, args.get("address"), args.get("name"))

    def _request_sync(self, args: dict):
        self._dispatch(self._push_state)

    def _do_init(self) -> bool:
        if self._stopped:
            return False
        try:
            self.bt = AstalBluetooth.Bluetooth.get_default()
            self.adapter = self.bt.get_adapter()

            def connect_sig(obj, name, cb):
                if obj:
                    sid = obj.connect(name, cb)
                    self._signal_ids.append((obj, sid))

            # Adapter/Manager Signals
            connect_sig(self.bt, "notify::is-powered", self._on_update)
            connect_sig(self.bt, "notify::is-connected", self._on_update)
            connect_sig(self.bt, "device-added", self._on_device_added)
            connect_sig(self.bt, "device-removed", self._on_update)
            connect_sig(self.bt, "adapter-added", self._on_update)

            if self.adapter:
                connect_sig(self.adapter, "notify::discovering", self._on_update)
                connect_sig(self.adapter, "notify::discoverable", self._on_update)
                connect_sig(self.adapter, "notify::pairable", self._on_update)
                connect_sig(self.adapter, "notify::alias", self._on_update)

            # Device Signals
            devices = self.bt.get_devices()
            for device in devices:
                self._connect_device_signals(device)

            self.is_ready = True
            log_info("AstalBluetoothService: Ready.")
            self._push_state()
        except Exception as e:
            log_error(f"AstalBluetoothService: Init failed: {e}")
        return False

    def _connect_device_signals(self, device):
        def connect_sig(obj, name, cb):
            if obj:
                sid = obj.connect(name, cb)
                self._signal_ids.append((obj, sid))

        # Watch ALL relevant properties
        connect_sig(device, "notify::connected", self._on_update)
        connect_sig(device, "notify::paired", self._on_update)
        connect_sig(device, "notify::trusted", self._on_update)
        connect_sig(device, "notify::blocked", self._on_update)
        connect_sig(device, "notify::rssi", self._on_update)
        connect_sig(device, "notify::alias", self._on_update)
        connect_sig(device, "notify::icon", self._on_update)
        connect_sig(device, "notify::battery-percentage", self._on_update)

    def _do_stop(self) -> bool:
        for obj, sid in self._signal_ids:
            try:
                if obj.handler_is_connected(sid):
                    obj.disconnect(sid)
            except Exception:
                pass
        self._signal_ids.clear()
        self.bt = None
        self.adapter = None
        self.is_ready = False
        return False

    def _do_toggle_power(self) -> bool:
        if self.bt:
            self.bt.toggle()
        return False

    def _do_toggle_scan(self, scanning: bool) -> bool:
        if not self.adapter:
            return False
        try:
            if scanning and not self.adapter.get_discovering():
                self.adapter.start_discovery()
            elif not scanning and self.adapter.get_discovering():
                self.adapter.stop_discovery()
        except Exception as e:
            log_error(f"BT Scan error: {e}")
        return False

    def _do_set_discoverable(self, val: bool) -> bool:
        if self.adapter:
            self.adapter.set_discoverable(val)
        return False

    def _do_set_pairable(self, val: bool) -> bool:
        if self.adapter:
            self.adapter.set_pairable(val)
        return False

    def _do_rename_adapter(self, name: str) -> bool:
        if self.adapter and name:
            self.adapter.set_alias(name)
        return False

    def _do_pair_device(self, address: str) -> bool:
        dev = self._find_device(address)
        if dev:
            try:
                # Pair can fail if already paired
                dev.pair()
            except Exception as e:
                log_error(f"BT Pair error: {e}")
        return False

    def _do_remove_device(self, address: str) -> bool:
        if not self.adapter:
            return False

        dev = self._find_device(address)
        if dev:
            try:
                self.adapter.remove_device(dev)
                log_info(f"AstalBluetooth: Removed device {address}")

                self._push_state()

                # Schedule another update in 250ms to ensure it disappears from the list
                GLib.timeout_add(250, self._push_state)

            except Exception as e:
                log_error(f"BT Remove error: {e}")
        return False

    def _do_set_trusted(self, address: str, val: bool) -> bool:
        dev = self._find_device(address)
        if dev:
            dev.set_trusted(val)
        return False

    def _do_set_blocked(self, address: str, val: bool) -> bool:
        dev = self._find_device(address)
        if dev:
            dev.set_blocked(val)
        return False

    def _do_rename_device(self, address: str, name: str) -> bool:
        dev = self._find_device(address)
        if dev and name:
            dev.set_alias(name)
        return False

    def _do_connect_device(self, address: str) -> bool:
        dev = self._find_device(address)
        if dev:
            try:
                dev.connect_device(None, None)
            except Exception as e:
                log_error(f"BT Connect error: {e}")
        return False

    def _do_disconnect_device(self, address: str) -> bool:
        dev = self._find_device(address)
        if dev:
            try:
                dev.disconnect_device(None, None)
            except Exception as e:
                log_error(f"BT Disconnect error: {e}")
        return False

    def _find_device(self, address: str):
        if not self.bt or not address:
            return None
        devices = self.bt.get_devices()
        for d in devices:
            if d.get_address() == address:
                return d
        return None

    def _on_device_added(self, bt, device):
        self._connect_device_signals(device)
        self._push_state()

    def _on_update(self, *args):
        self._push_state()

    def _push_state(self) -> bool:
        if self._stopped or not self.bt:
            return False

        try:
            adapter_info = {
                "powered": self.bt.get_is_powered(),
                "name": self.adapter.get_alias() if self.adapter else "Unknown",
                "scanning": self.adapter.get_discovering() if self.adapter else False,
                "discoverable": (
                    self.adapter.get_discoverable() if self.adapter else False
                ),
                "pairable": self.adapter.get_pairable() if self.adapter else False,
                "address": self.adapter.get_address() if self.adapter else "",
            }

            devices_list = []
            devices = self.bt.get_devices()

            for dev in devices:
                devices_list.append(
                    {
                        "name": dev.get_alias() or dev.get_name(),
                        "address": dev.get_address(),
                        "icon": dev.get_icon(),
                        "paired": dev.get_paired(),
                        "connected": dev.get_connected(),
                        "trusted": dev.get_trusted(),
                        "blocked": dev.get_blocked(),
                        "rssi": dev.get_rssi(),
                        "battery": dev.get_battery_percentage(),
                        "legacy": dev.get_legacy_pairing(),
                    }
                )

            # Sort: Connected, then Paired, then Signal Strength (RSSI)
            devices_list.sort(
                key=lambda x: (not x['connected'], not x['paired'], -x['rssi'])
            )

            payload = json.dumps({"adapter": adapter_info, "devices": devices_list})
            self._setState(payload)
        except Exception as e:
            log_error(f"AstalBluetooth: State push failed: {e}")

        return False


__all__ = ["AstalBluetoothService", "BluetoothServiceArgs"]
