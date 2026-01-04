import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..gi_modules import Gio, GLib, GObject, Gtk
from ..log import log_error, log_info
from .base import WeLDService


class TrayService(WeLDService):
    def __init__(self, setState: Callable[[str], None], arguments: dict):
        super().__init__(setState)
        self._stopped = False
        self._items: Dict[str, Dict] = {}
        self._watcher_proxy = None

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        GLib.idle_add(self._do_init)
        return (
            self._stop,
            {
                "Tray:invoke": self._invoke_menu_item,
                "Tray:activate": self._activate_item,
                "Tray:sync": lambda _: self._push_state(),
            },
        )

    def _do_init(self):
        try:
            self._watcher_proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
                None,
            )

            self._watcher_proxy.connect("g-signal", self._on_watcher_signal)

            items = self._watcher_proxy.get_cached_property(
                "RegisteredStatusNotifierItems"
            )
            if items:
                for bus_id in items.unpack():
                    self._add_item(bus_id)

            self._push_state()
            log_info("TrayService: Running")
        except Exception as e:
            log_error(f"Watcher Init Fail: {e}")

    def _on_watcher_signal(self, proxy, sender, signal, params):
        bus_id = params.unpack()[0]
        if signal == "StatusNotifierItemRegistered":
            self._add_item(bus_id)
        elif signal == "StatusNotifierItemUnregistered":
            self._remove_item(bus_id)

    def _add_item(self, bus_id: str):
        if bus_id in self._items:
            return

        parts = bus_id.split("/", 1)
        bus_name = parts[0]
        obj_path = "/" + parts[1] if len(parts) > 1 else "/StatusNotifierItem"

        try:
            item_proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.NONE,
                None,
                bus_name,
                obj_path,
                "org.kde.StatusNotifierItem",
                None,
            )

            menu_path = item_proxy.get_cached_property("Menu")
            menu_proxy = None
            if menu_path:
                menu_proxy = Gio.DBusProxy.new_for_bus_sync(
                    Gio.BusType.SESSION,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    bus_name,
                    menu_path.unpack(),
                    "com.canonical.dbusmenu",
                    None,
                )
                menu_proxy.connect("g-signal", lambda *_: self._push_state())

            self._items[bus_id] = {
                "item_proxy": item_proxy,
                "menu_proxy": menu_proxy,
                "bus_name": bus_name,
            }
            self._push_state()
        except Exception as e:
            log_error(f"Failed to proxy item {bus_id}: {e}")

    def _remove_item(self, bus_id: str):
        if bus_id in self._items:
            del self._items[bus_id]
            self._push_state()

    def _parse_layout(self, layout_tuple) -> Optional[Dict]:
        menu_id, props, children = layout_tuple

        label = props.get("label", "")
        label = label.replace("_", "") if label else ""

        enabled = props.get("enabled", True)
        visible = props.get("visible", True)

        if not visible:
            return None

        is_checked = props.get("toggle-state", 0) == 1

        parsed_children = []
        for child_variant in children:
            child_data = self._parse_layout(child_variant)
            if child_data:
                parsed_children.append(child_data)

        return {
            "id": menu_id,
            "label": label,
            "enabled": enabled,
            "isChecked": is_checked,
            "submenu": parsed_children,
        }

    def _push_state(self):
        if self._stopped:
            return False
        try:
            payload = []
            for bus_id, proxies in self._items.items():
                item = proxies["item_proxy"]

                title = item.get_cached_property("Title")
                icon_name = item.get_cached_property("IconName")
                theme_path = item.get_cached_property("IconThemePath")

                menu_data = []
                if proxies["menu_proxy"]:
                    try:
                        res = proxies["menu_proxy"].call_sync(
                            "GetLayout",
                            GLib.Variant("(iias)", (0, -1, [])),
                            Gio.DBusCallFlags.NONE,
                            -1,
                            None,
                        )
                        _, layout_tuple = res.unpack()
                        root_parsed = self._parse_layout(layout_tuple)
                        if root_parsed:
                            menu_data = root_parsed["submenu"]
                    except Exception as me:
                        log_error(f"Menu fetch error for {bus_id}: {me}")

                payload.append(
                    {
                        "id": bus_id,
                        "title": title.unpack() if title else bus_id,
                        "icon": self._resolve_icon(
                            icon_name.unpack() if icon_name else "",
                            theme_path.unpack() if theme_path else "",
                        ),
                        "menu": menu_data,
                    }
                )

            self._setState(json.dumps({"items": payload}))
        except Exception as e:
            log_error(f"Tray Push Error: {e}")
        return False

    def _resolve_icon(self, name, theme_path) -> str:
        if not name:
            return ""
        if name.startswith("/"):
            return f"weld://{name}"
        theme = Gtk.IconTheme.get_default()
        if theme_path:
            theme.append_search_path(theme_path)
        info = theme.lookup_icon(name, 32, 0)
        return f"weld://{info.get_filename()}" if info else ""

    def _invoke_menu_item(self, args):
        proxies = self._items.get(args["bus_id"])
        if proxies and proxies["menu_proxy"]:
            proxies["menu_proxy"].call_sync(
                "Event",
                GLib.Variant(
                    "(isvu)",
                    (int(args["menu_id"]), "clicked", GLib.Variant("s", ""), 0),
                ),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )

    def _activate_item(self, args):
        proxies = self._items.get(args["id"])
        if proxies:
            proxies["item_proxy"].call_sync(
                "Activate",
                GLib.Variant("(ii)", (0, 0)),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )

    def _stop(self):
        self._stopped = True
        self._items.clear()
