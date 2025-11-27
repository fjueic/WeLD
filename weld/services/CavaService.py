import os
import subprocess
import tempfile
from typing import Callable, Dict, NotRequired, Optional, Tuple, TypedDict

from ..gi_modules import Gio, GLib, Soup, WebKit2
from ..log import log_error, log_info
from .base import WeLDService

_SCHEME_REGISTERED = False


class CavaServiceArgs(TypedDict):
    bars: NotRequired[int]
    framerate: NotRequired[int]
    autosens: NotRequired[bool]
    high_cutoff: NotRequired[int]
    low_cutoff: NotRequired[int]
    noise_reduction: NotRequired[float]
    samplerate: NotRequired[int]
    source: NotRequired[str]
    stereo: NotRequired[bool]
    channels: NotRequired[int]
    input: NotRequired[str]


class CavaService(WeLDService):
    _active_instance: Optional['CavaService'] = None

    def __init__(self, setState: Callable[[str], None], arguments: CavaServiceArgs):
        super().__init__(setState)
        self.arguments = arguments
        self.process: Optional[subprocess.Popen] = None
        self.config_path: Optional[str] = None
        self._stopped = False
        self._bars = arguments.get("bars", 12)
        self._framerate = arguments.get("framerate", 60)

    def start(self) -> Tuple[Callable[[], None], Dict[str, Callable]]:
        log_info("Starting CavaService...")

        CavaService._active_instance = self

        self._register_global_scheme()
        handlers = {
            "cava:set_config": self._set_config,
            "cava:toggle": self._toggle_active,
        }
        return (self._stop, handlers)

    def _stop(self):
        self._stopped = True

        if CavaService._active_instance == self:
            CavaService._active_instance = None

        self._kill_process()

    def _register_global_scheme(self):
        global _SCHEME_REGISTERED
        if _SCHEME_REGISTERED:
            return

        try:
            context = WebKit2.WebContext.get_default()
            sm = context.get_security_manager()
            sm.register_uri_scheme_as_secure("cava")
            sm.register_uri_scheme_as_cors_enabled("cava")

            context.register_uri_scheme("cava", CavaService._global_uri_handler)
            _SCHEME_REGISTERED = True
            log_info("Registered global 'cava://' URI scheme.")
        except Exception as e:
            log_error(f"Failed to register Cava scheme: {e}")

    @staticmethod
    def _global_uri_handler(request):
        """Static dispatcher that routes request to the active instance."""
        instance = CavaService._active_instance
        if instance and not instance._stopped:
            instance._handle_uri_request(request)
        else:
            err = GLib.Error.new_literal(
                Gio.io_error_quark(),
                "Service Stopped",
                Gio.IOErrorEnum.NOT_FOUND,
            )
            request.finish_error(err)

    def _handle_uri_request(self, request):
        uri = request.get_uri()
        if uri == "cava://stream":
            self._handle_stream_request(request)
        else:
            err = GLib.Error.new_literal(
                Gio.io_error_quark(),
                "Not Found",
                GLib.FileError.FAILED,
            )
            request.finish_error(err)
            request.finish_error(err)

    def _handle_stream_request(self, request):
        if not self.process or self.process.poll() is not None:
            self._spawn_process()

        if not self.process:
            err = GLib.Error.new_literal(
                Gio.io_error_quark(),
                "Cava failed to start",
                GLib.FileError.FAILED,
            )
            request.finish_error(err)
            return

        try:
            master_fd = self.process.stdout.fileno()
            fresh_fd = os.dup(master_fd)
            g_stream = Gio.UnixInputStream.new(fresh_fd, True)

            response = WebKit2.URISchemeResponse.new(g_stream, -1)
            response.set_status(200, "OK")
            response.set_content_type("text/plain")

            headers = Soup.MessageHeaders.new(Soup.MessageHeadersType.RESPONSE)
            headers.append("Access-Control-Allow-Origin", "*")
            headers.append("Access-Control-Allow-Methods", "GET")

            response.set_http_headers(headers)
            request.finish_with_response(response)

            log_info("Piped Cava stdout to WebKit.")

        except Exception as e:
            log_error(f"Stream pipe error: {e}")
            err = GLib.Error.new_literal(
                GLib.FileError.quark(),
                str(e),
                GLib.FileError.FAILED,
            )
            request.finish_error(err)

    def _spawn_process(self) -> bool:
        if self._stopped:
            return False
        self._create_config_file()
        try:
            self.process = subprocess.Popen(
                ["cava", "-p", self.config_path],
                stdout=subprocess.PIPE,
                stderr=None,
                bufsize=1024,
                text=False,
            )
            return True
        except Exception as e:
            log_error(f"Failed to spawn Cava: {e}")
            return False

    def _create_config_file(self):
        if self.config_path and os.path.exists(self.config_path):
            os.remove(self.config_path)

        fd, path = tempfile.mkstemp(
            prefix="weld_cava_", suffix=".conf", dir="/tmp/weld"
        )
        self.config_path = path
        args = self.arguments

        input_method = args.get("input", "pulse")
        source = args.get("source", "auto")
        low_cutoff = args.get("low_cutoff", 50)
        high_cutoff = args.get("high_cutoff", 10000)
        sample_rate = args.get("samplerate", 44100)

        is_stereo = args.get("stereo", False) or args.get("channels", 1) == 2
        channels_str = "stereo" if is_stereo else "mono"

        config_content = f"""
[general]
framerate = {self._framerate}
bars = {self._bars}
autosens = {1 if args.get("autosens", True) else 0}
lower_cutoff_freq = {low_cutoff}
higher_cutoff_freq = {high_cutoff}

[input]
method = {input_method}
source = {source}
sample_rate = {sample_rate}

[output]
method = raw
channels = {channels_str}
data_format = ascii
ascii_max_range = 1000
bar_delimiter = 44
frame_delimiter = 10
"""
        if "noise_reduction" in args:
            config_content += (
                f"\n[smoothing]\nnoise_reduction = {args['noise_reduction']}\n"
            )

        with os.fdopen(fd, 'w') as f:
            f.write(config_content)

    def _kill_process(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                log_info("Cava process stuck, force killing...")
                try:
                    self.process.kill()
                    self.process.wait()
                except:
                    pass
            except Exception:
                pass
            self.process = None

        if self.config_path and os.path.exists(self.config_path):
            try:
                os.remove(self.config_path)
            except:
                pass

    def _toggle_active(self, args: dict):
        active = args.get("active")
        is_running = self.process is not None and self.process.poll() is None
        target = active if active is not None else not is_running
        if not target and is_running:
            self._kill_process()

    def _set_config(self, args: dict):
        self.arguments.update(args)  # type: ignore
        if "bars" in args:
            self._bars = int(args["bars"])
        if "framerate" in args:
            self._framerate = int(args["framerate"])
        self._kill_process()


__all__ = ["CavaService", "CavaServiceArgs"]
