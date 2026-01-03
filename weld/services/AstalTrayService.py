import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import gi

from ..gi_modules import Gio, GLib, GObject, Gtk
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalTray", "0.1")
from gi.repository import AstalTray


class AstalTrayService(WeLDService):
    def __init__(self, setState: Callable[[str], None], arguments: dict):
        super().__init__(setState)
        self.tray: AstalTray.Tray = None  # type: ignore
        self._stopped = False
        self._signal_ids: List[Tuple[GObject.Object, int]] = []

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        GLib.idle_add(self._do_init)
        return (
            self._stop,
            {
                "AstalTray:activate": self._activate,
                "AstalTray:secondary_activate": self._secondary_activate,
                "AstalTray:scroll": self._scroll,
                "AstalTray:invoke_action": self._invoke_action,
                "AstalTray:about_to_show": self._about_to_show,
                "AstalTray:sync": lambda _: self._push_state(),
            },
        )

    def _connect_safe(self, obj, sig, cb):
        if obj:
            sid = obj.connect(sig, cb)
            self._signal_ids.append((obj, sid))

    def _do_init(self) -> bool:
        try:
            self.tray = AstalTray.Tray.get_default()
            self._connect_safe(self.tray, "item-added", self._on_item_added)
            self._connect_safe(self.tray, "item-removed", self._on_update)
            for item in self.tray.get_items():
                self._setup_item(item)
            GLib.timeout_add(100, self._push_state)
            log_info("AstalTrayService: Initialized (Icons Disabled).")
        except Exception as e:
            log_error(f"AstalTray Init Failed: {e}")
        return False

    def _setup_item(self, item):
        self._connect_safe(item, "ready", self._on_update)
        self._connect_safe(item, "changed", self._on_update)

    def _on_item_added(self, tray, item_id):
        item = tray.get_item(item_id)
        if item:
            self._setup_item(item)
        self._push_state()

    def _on_update(self, *args):
        self._push_state()

    def _parse_menu_model(self, model: Gio.MenuModel) -> List[Dict]:
        items = []
        if not model:
            return items

        for i in range(model.get_n_items()):

            def get_attr(key):
                v = model.get_item_attribute_value(i, key, None)
                return v.unpack() if v else None

            # Standard Info
            label = get_attr("label")
            action = get_attr("action")

            is_checked = False
            target = get_attr("target")
            if target is not None:
                is_checked = (
                    bool(target)
                    if not isinstance(target, str)
                    else (target == "1" or target.lower() == "true")
                )

            ts = get_attr("toggle-state")
            if ts is not None:
                is_checked = ts == 1

            icon_v = model.get_item_attribute_value(i, "icon", None)
            if icon_v:
                gicon = Gio.Icon.deserialize(icon_v)
                if isinstance(gicon, Gio.ThemedIcon):
                    for name in gicon.get_names():
                        if "checked" in name.lower():
                            is_checked = True

            enabled = get_attr("enabled")
            if enabled is None:
                enabled = get_attr("sensitive")

            submenu = model.get_item_link(i, Gio.MENU_LINK_SUBMENU)
            section = model.get_item_link(i, Gio.MENU_LINK_SECTION)

            if section:
                items.extend(self._parse_menu_model(section))
                continue

            items.append(
                {
                    "label": label,
                    "action": action,
                    "isChecked": is_checked,
                    "enabled": enabled if enabled is not None else True,
                    "submenu": self._parse_menu_model(submenu) if submenu else None,
                }
            )
        return items

    def _push_state(self):
        if not self.tray or self._stopped:
            return False
        try:
            payload = []
            for item in self.tray.get_items():
                payload.append(
                    {
                        "id": item.get_item_id(),
                        "title": item.get_title(),
                        "icon": self._resolve_icon(item),
                        "status": int(item.get_status()),
                        "menu": (
                            self._parse_menu_model(item.get_menu_model())
                            if item.get_menu_model()
                            else []
                        ),
                    }
                )
            self._setState(json.dumps({"items": payload}))
        except Exception as e:
            log_error(f"Tray State Error: {e}")
        return False

    def _resolve_icon(self, item) -> str:
        name = item.get_icon_name()
        if not name:
            return ""
        if name.startswith("/"):
            return f"weld://{name}"
        theme = Gtk.IconTheme.get_default()
        path = item.get_icon_theme_path()
        if path:
            theme.append_search_path(path)
        info = theme.lookup_icon(name, 32, 0)
        return f"weld://{info.get_filename()}" if info else ""

    def _invoke_action(self, args):
        item = self.tray.get_item(args["id"])
        if item and item.get_action_group():
            action = args["action"].split(".")[-1]
            item.get_action_group().activate_action(action, None)

    def _about_to_show(self, args):
        item = self.tray.get_item(args["id"])
        if item:
            item.about_to_show()
            GLib.timeout_add(150, self._push_state)

    def _activate(self, args):
        item = self.tray.get_item(args["id"])
        if item:
            item.activate(args["x"], args["y"])

    def _secondary_activate(self, args):
        item = self.tray.get_item(args["id"])
        if item:
            item.secondary_activate(args["x"], args["y"])

    def _scroll(self, args):
        item = self.tray.get_item(args["id"])
        if item:
            item.scroll(args["delta"], "vertical")

    def _stop(self):
        self._stopped = True
        for obj, sid in self._signal_ids:
            try:
                if obj.handler_is_connected(sid):
                    obj.disconnect(sid)
            except:
                pass
        self._signal_ids.clear()
        self.tray = None
