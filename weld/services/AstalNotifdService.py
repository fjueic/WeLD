import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import gi

from ..gi_modules import GLib, GObject, Gtk
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalNotifd", "0.1")
from gi.repository import AstalNotifd


class AstalNotifdService(WeLDService):
    def __init__(self, setState: Callable[[str], None], arguments: dict):
        super().__init__(setState)
        self.notifd: AstalNotifd.Notifd = None  # type: ignore
        self._signal_ids = []

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        GLib.idle_add(self._do_init)

        # Mapping every exposed method to a handler
        handlers = {
            "AstalNotifd:dismiss": self._dismiss,
            "AstalNotifd:expire": self._expire,
            "AstalNotifd:invoke": self._invoke,
            "AstalNotifd:set_dnd": self._set_dnd,
            "AstalNotifd:set_ignore_timeout": self._set_ignore_timeout,
            "AstalNotifd:set_default_timeout": self._set_default_timeout,
            "AstalNotifd:clear_all": self._clear_all,
            "AstalNotifd:send_test": self._send_test_notification,  # Uses send_notification()
            "AstalNotifd:sync": lambda _: self._push_state(),
        }
        return (self._stop, handlers)

    def _do_init(self) -> bool:
        try:
            self.notifd = AstalNotifd.Notifd.get_default()

            # Connect to Daemon Signals
            self._signal_ids.append(self.notifd.connect("notified", self._on_update))
            self._signal_ids.append(self.notifd.connect("resolved", self._on_update))

            # Connect to Daemon Property Notifiers
            for prop in ["dont-disturb", "ignore-timeout", "default-timeout"]:
                self._signal_ids.append(
                    self.notifd.connect(f"notify::{prop}", self._on_update)
                )

            self._push_state()
            log_info("AstalNotifd: Full functionality service ready.")
        except Exception as e:
            log_error(f"Notifd Exhaustive Init Failed: {e}")
        return False

    def _on_update(self, *args):
        self._push_state()

    def _push_state(self):
        if not self.notifd:
            return False

        notifs_list = []
        for n in self.notifd.get_notifications():
            notifs_list.append(
                {
                    "id": n.get_id(),
                    "state": int(n.get_state()),
                    "appName": n.get_app_name(),
                    "appIcon": self._resolve_path(n.get_app_icon()),
                    "summary": n.get_summary(),
                    "body": n.get_body(),
                    "time": n.get_time(),
                    "urgency": int(n.get_urgency()),
                    "expireTimeout": n.get_expire_timeout(),
                    "image": self._resolve_path(n.get_image()),
                    "category": n.get_category(),
                    "desktopEntry": n.get_desktop_entry(),
                    "resident": n.get_resident(),
                    "suppressSound": n.get_suppress_sound(),
                    "transient": n.get_transient(),
                    "x": n.get_x(),
                    "y": n.get_y(),
                    "actions": [
                        {"id": a.get_id(), "label": a.get_label()}
                        for a in n.get_actions()
                    ],
                }
            )

        self._setState(
            json.dumps(
                {
                    "daemon": {
                        "dontDisturb": self.notifd.get_dont_disturb(),
                        "ignoreTimeout": self.notifd.get_ignore_timeout(),
                        "defaultTimeout": self.notifd.get_default_timeout(),
                    },
                    "notifications": sorted(
                        notifs_list, key=lambda x: x['time'], reverse=True
                    ),
                }
            )
        )
        return False

    def _resolve_path(self, path: str) -> str:
        if not path:
            return ""
        if path.startswith("/"):
            return f"weld://{path}"
        # Themed icon resolution
        theme = Gtk.IconTheme.get_default()
        info = theme.lookup_icon(path, 48, 0)
        return f"weld://{info.get_filename()}" if info else ""

    # --- Method Implementations ---
    def _dismiss(self, args):
        n = self.notifd.get_notification(args.get("id"))
        if n:
            n.dismiss()

    def _expire(self, args):
        n = self.notifd.get_notification(args.get("id"))
        if n:
            n.expire()

    def _invoke(self, args):
        n = self.notifd.get_notification(args.get("id"))
        if n:
            n.invoke(args.get("action_id"))

    def _set_dnd(self, args):
        self.notifd.set_dont_disturb(args.get("val", True))

    def _set_ignore_timeout(self, args):
        self.notifd.set_ignore_timeout(args.get("val", True))

    def _set_default_timeout(self, args):
        self.notifd.set_default_timeout(args.get("val", -1))

    def _clear_all(self, _):
        for n in self.notifd.get_notifications():
            n.dismiss()

    def _send_test_notification(self, args):
        """Uses the global send_notification functionality from the GIR."""
        notif = AstalNotifd.Notification.new()
        notif.set_app_name("WeLD System")
        notif.set_summary(args.get("summary", "Test Notification"))
        notif.set_body(args.get("body", "This is an internal test notification."))
        notif.set_urgency(AstalNotifd.Urgency.NORMAL)
        # Adding a custom action
        action = AstalNotifd.Action.new("test-action", "Click Me")
        notif.add_action(action)

        AstalNotifd.send_notification(notif, None, None)

    def _stop(self):
        for sid in self._signal_ids:
            if self.notifd:
                self.notifd.disconnect(sid)
        self.notifd = None


__all__ = ["AstalNotifdService"]
