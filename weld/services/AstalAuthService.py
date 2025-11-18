# AUTHENTICATION SERVICE (AstalAuth)
import json
from typing import Any, Callable, Dict, List, NotRequired, Optional, Tuple, TypedDict

import gi

from ..gi_modules import GLib
from ..log import log_error, log_info
from .base import WeLDService

gi.require_version("AstalAuth", "0.1")
from gi.repository import AstalAuth


class AuthServiceArgs(TypedDict):
    username: NotRequired[str]
    service: NotRequired[str]


class AstalAuthService(WeLDService):
    """
    Service to handle PAM authentication using AstalAuth.
    """

    def __init__(self, setState: Callable[[str], None], arguments: AuthServiceArgs):
        super().__init__(setState)
        self.arguments = arguments

        self.pam: Optional[AstalAuth.Pam] = None
        self.is_ready = False
        self._stopped = False
        self._signal_ids: List[int] = []

        if AstalAuth is None:
            log_error("AstalAuthService: AstalAuth library not found.")

        log_info("AstalAuthService: Initialized on worker thread.")

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        if AstalAuth is None:
            return (lambda: None, {})

        GLib.idle_add(self._do_init)

        handlers = {
            "AstalAuth:start": self._start_auth,
            "AstalAuth:secret": self._supply_secret,
            "AstalAuth:cancel": self._cancel_auth,
        }
        return (self._stop, handlers)

    def _stop(self):
        """Stop the AstalAuthService."""
        self._stopped = True
        log_info("Stopping AstalAuthService...")

        GLib.idle_add(self._do_stop)

    def _start_auth(self, args: dict):
        if self._stopped:
            return

        if not self.is_ready:
            log_error("AstalAuthService: Cannot start, service not ready.")
            return
        GLib.idle_add(self._do_start_auth)

    def _supply_secret(self, args: dict):
        if self._stopped:
            return

        if not self.is_ready:
            log_error("AstalAuthService: Cannot supply secret, service not ready.")
            return
        secret = args.get("secret")
        GLib.idle_add(self._do_supply_secret, secret)

    def _cancel_auth(self, args: dict):
        if self._stopped:
            return

        if not self.is_ready:
            log_error("AstalAuthService: Cannot cancel, service not ready.")
            return
        GLib.idle_add(self._do_supply_secret, None)

    def _do_init(self) -> bool:
        if self._stopped:
            return False

        try:
            self.pam = AstalAuth.Pam()
            username = self.arguments.get("username", GLib.get_user_name())
            service = self.arguments.get("service", "polkit-1")

            self.pam.set_username(username)
            self.pam.set_service(service)

            log_info(
                f"AstalAuthService: Initializing for user='{username}', service='{service}'"
            )

            def connect_sig(name, cb):
                if self.pam:
                    sid = self.pam.connect(name, cb)
                    self._signal_ids.append(sid)

            connect_sig("auth-prompt-visible", self._on_prompt_visible)
            connect_sig("auth-prompt-hidden", self._on_prompt_hidden)
            connect_sig("auth-info", self._on_info)
            connect_sig("auth-error", self._on_error)
            connect_sig("success", self._on_success)
            connect_sig("fail", self._on_fail)

            self.is_ready = True
            log_info("AstalAuthService: GObject initialization complete.")

        except Exception as e:
            log_error(f"AstalAuthService: Failed to initialize: {e}")

        return False

    def _do_stop(self) -> bool:
        """Clean up the GObject and disconnect signals."""
        if self.pam:
            for sid in self._signal_ids:
                try:
                    if self.pam.handler_is_connected(sid):
                        self.pam.disconnect(sid)
                except Exception:
                    pass
            self._signal_ids.clear()

            self.pam = None

        self.is_ready = False
        log_info("AstalAuthService: GObject cleanup complete.")
        return False

    def _do_start_auth(self) -> bool:
        if self.pam and not self._stopped:
            log_info("AstalAuthService: Starting authentication flow...")
            self.pam.start_authenticate()
        return False

    def _do_supply_secret(self, secret: Optional[str]) -> bool:
        if self.pam and not self._stopped:
            log_info("AstalAuthService: Supplying secret to PAM...")
            self.pam.supply_secret(secret)
        return False

    def _send_state(self, status: str, message: str):
        if self._stopped:
            return
        try:
            payload = json.dumps({"status": status, "message": message})
            self._setState(payload)
        except Exception as e:
            log_error(f"AstalAuthService: Failed to serialize state: {e}")

    def _on_prompt_visible(self, pam_obj, msg: str) -> bool:
        self._send_state("prompt_visible", msg)
        return False

    def _on_prompt_hidden(self, pam_obj, msg: str) -> bool:
        self._send_state("prompt_hidden", msg)
        return False

    def _on_info(self, pam_obj, msg: str) -> bool:
        self._send_state("info", msg)
        return False

    def _on_error(self, pam_obj, msg: str) -> bool:
        self._send_state("error", msg)
        return False

    def _on_success(self, pam_obj) -> bool:
        self._send_state("success", "Authentication Succeeded")
        return False

    def _on_fail(self, pam_obj, msg: str) -> bool:
        self._send_state("fail", "Authentication Failed")
        return False


__all__ = ["AstalAuthService", "AuthServiceArgs"]
