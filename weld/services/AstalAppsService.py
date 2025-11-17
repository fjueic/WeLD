import json
import re
import shlex
import subprocess
import threading
from typing import Any, Callable, Dict, List, NotRequired, Optional, Tuple, TypedDict

import gi
from gi.repository import Gio, GLib

from ..log import log_error, log_info
from .base import WeLDService


class AppMultipliers(TypedDict):
    name: NotRequired[float]


class AppsServiceArgs(TypedDict):
    """
    Configuration options for the AstalAppsService.
    """

    queryLimit: NotRequired[int]
    showHidden: NotRequired[bool]
    minScore: NotRequired[float]
    multipliers: NotRequired[AppMultipliers]


class AstalAppsService(WeLDService):
    """
    Service to query and launch system applications.
    This version uses the stable Gio.DesktopAppInfo for discovery
    and subprocess.Popen for launch. I am not able to get applications
    to launch properly using Astal.
    """

    def __init__(self, setState: Callable[[str], None], arguments: AppsServiceArgs):
        """Initialize the AstalAppsService."""
        super().__init__(setState)
        self.query_limit = arguments.get("queryLimit", 10)
        self.show_hidden = arguments.get("showHidden", False)

        self.app_list: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

        log_info("AstalAppsService: Starting app loader thread...")
        self.loader_thread = threading.Thread(target=self._load_apps, daemon=True)
        self.loader_thread.start()

    def _load_apps(self):
        log_info("AstalAppsService: Loading applications")
        temp_apps = []

        try:
            all_app_infos = Gio.DesktopAppInfo.get_all()

            for app_info in all_app_infos:
                if not self.show_hidden and app_info.get_nodisplay():
                    continue

                name = app_info.get_name()
                comment = app_info.get_description()
                entry_id = app_info.get_id()

                searchable_string = (
                    f"{name or ''} {comment or ''} {entry_id or ''}".lower()
                )

                temp_apps.append(
                    {
                        "name": name,
                        "description": comment,
                        "icon": (
                            app_info.get_icon().to_string()
                            if app_info.get_icon()
                            else None
                        ),
                        "entry": entry_id,
                        "wmClass": app_info.get_startup_wm_class(),
                        "keywords": app_info.get_keywords() or [],
                        "categories": app_info.get_categories() or [],
                        "exec": app_info.get_string("Exec"),
                        "_search_": searchable_string,
                    }
                )
        except Exception as e:
            log_error(f"AstalAppsService: Failed to load apps: {e}")

        with self.lock:
            self.app_list = temp_apps

        log_info(f"AstalAppsService: Loader finished. Found {len(temp_apps)} apps.")

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        handlers = {
            "apps:query": self._query,
            "apps:launch": self._launch,
            "apps:reload": self._reload,
        }
        return (self._stop, handlers)

    def _stop(self):
        log_info("Stopping AstalAppsService...")

    def _reload(self, args: dict):
        log_info("AstalAppsService: Reload requested.")
        with self.lock:
            self.app_list = []
        self.loader_thread = threading.Thread(target=self._load_apps, daemon=True)
        self.loader_thread.start()

    def _launch(self, args: dict):
        """
        Handler to launch an application.
        """
        entry_str = args.get("entry")
        if not entry_str:
            log_error("AstalAppsService: 'apps:launch' called without 'entry'.")
            return

        app_to_launch = None
        with self.lock:
            for app in self.app_list:
                if app.get("entry") == entry_str:
                    app_to_launch = app
                    break

        if not app_to_launch or not app_to_launch.get("exec"):
            log_error(
                f"AstalAppsService: Could not find app or 'Exec' key for: {entry_str}"
            )
            return

        try:
            exec_cmd = app_to_launch["exec"]
            cleaned_exec_cmd = re.sub(r"%\w", "", exec_cmd).strip()
            cmd_list = shlex.split(cleaned_exec_cmd)

            subprocess.Popen(
                cmd_list,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            log_info(f"AstalAppsService: Launched '{entry_str}' in new session.")
        except Exception as e:
            log_error(f"AstalAppsService: Popen launch failed for '{entry_str}': {e}")

    def _query(self, args: dict):
        """
        Handler to query applications. This is thread-safe.
        """
        query_str = args.get("query", "").lower()

        if not query_str:
            self._setState("[]")
            return

        results = []
        try:
            with self.lock:
                if not self.app_list:
                    self._setState("[]")
                    return

                for app in self.app_list:
                    if len(results) >= self.query_limit:
                        break

                    search_string = app.get("_search_", "")
                    it = iter(search_string)
                    if all(c in it for c in query_str):
                        results.append(app)

            state_string = json.dumps(results)
            self._setState(state_string)
        except Exception as e:
            log_error(f"AstalAppsService: Query failed for '{query_str}': {e}")
            self._setState("[]")


__all__ = ["AstalAppsService", "AppsServiceArgs"]
