from __future__ import annotations

import json
import os
import socket
from typing import Callable, List, Optional

from pydantic import ValidationError, parse_obj_as

from weld.constants import (
    CONFIG_FILE,
    INPUT_MASK_JS,
    PATH_TO_INTERPETER,
    SCRIPT_MESSAGE_HANDLER,
    SCRIPT_MESSAGE_RECEIVED_SIGNAL,
    SOCKET_PATH,
    SOURCE_HTML,
    SYNC_DIMENSIONS_JS,
    TEXT_ENCODING,
    WELD_BIND,
    WIDGET_DIR,
)
from weld.gi_modules import Gdk, GLib, Gtk, GtkLayerShell, WebKit2
from weld.log import log_debug, log_error, log_exception, log_info, log_warning
from weld.type import (
    AnchorType,
    Config,
    FocusType,
    JSMessage,
    LayerType,
    PayloadType,
    State,
    UpdateStrategy,
)
from weld.type.cli import CliOptions
from weld.type.payload import ConfigureGTKLayerShellPayloadData
from weld.utils import (
    run_continuous_cmd,
    run_detached_cmd,
    run_unix_socket_threaded,
    set_interval,
)
from weld.utils.data_fetching import run_cmd_non_block


class WidgetWindow(Gtk.Window):
    """A class that represents a window with a WebKit2 WebView."""

    path: str
    config: Config
    name: str
    view: WebKit2.WebView
    states: List[State]
    interval_runners: List[Callable[[], None]]
    processes: List[Callable[[], None]]
    manual_states: dict[str, Callable[[Optional[dict[str, str]]], None]]
    masks: list[tuple[int, int, int, int]]
    base_webview: BaseWebView
    bindings: list[str]

    def __init__(self, name: str, base_webview: BaseWebView):
        self.base_webview = base_webview
        self.manual_states = {}
        self.interval_runners = []
        self.processes = []
        self.name = name
        self.states = []
        self.bindings = []
        self.path = os.path.join(WIDGET_DIR, name)
        try:
            with open(os.path.join(self.path, CONFIG_FILE), "r") as f:
                var = {}
                exec(f.read(), var)
                if "config" not in var:
                    log_error(f"Config not found for {self.name}.")
                    log_error(f"Skipping {self.name} as not widget.")
                    return
                try:
                    self.config = Config(**var["config"])
                except ValidationError as e:
                    log_error(f"Validation error loading config for {self.name}: {e}")
                    log_error(f"Skipping {self.name} as not a widget.")
                    return
                if "states" in var:
                    try:
                        self.states = [State(**state) for state in var["states"]]
                    except ValidationError as e:
                        log_error(
                            f"Validation error loading states for {self.name}: {e}"
                        )
                        log_error(f"Skipping {self.name} as not a widget.")
                        return
                    log_debug(f"Loaded states for {self.name}: {self.states}")
                else:
                    log_warning(f"No states found for {self.name}.")
                if "binds" in var:
                    for bind in var["binds"]:
                        self.base_webview.bindings[self.name + bind["function"]] = {
                            "widget": self.name,
                            "function": bind["function"],
                            "bind_event": bind["bind_event"],
                        }
                        self.bindings.append(self.name + bind["function"])
                        print(self.base_webview.bindings)
                    self.base_webview.refresh_binds()

        except FileNotFoundError:
            log_error(f"Config file not found for {self.name}.")
            log_error(f"Skipping {self.name} as not widget.")
            return
        super().__init__(title=self.config.title)
        self.view = WebKit2.WebView.new_with_related_view(self.base_webview.view)

        self.view.set_size_request(1024, 768)
        if self.config:
            self.configure_GTKLayerShell()

        # Disable caching in the WebView settings
        settings = self.view.get_settings()
        settings.set_property("enable-offline-web-application-cache", False)
        settings.set_property("enable-page-cache", False)
        settings.set_property("enable-html5-local-storage", False)
        if self.config.url:
            file_uri = self.config.url
        else:
            local_file_path = os.path.join(self.path, SOURCE_HTML)
            if not os.path.exists(local_file_path):
                log_error(f"File not found: {local_file_path}")
                log_error(f"Skipping {self.name} as not a widget.")
                return
            file_uri = f"file://{os.path.abspath(local_file_path)}"
        log_info(f"Loading URI: {file_uri}")
        self.view.load_uri(file_uri)
        self.add(self.view)
        self.base_webview.widgets[name] = self
        self.show_all()
        self.connect("destroy", self.close)
        self.set_window_transparency()
        self.view.connect("load-changed", self.after_load)
        manager = self.view.get_user_content_manager()
        manager.register_script_message_handler(SCRIPT_MESSAGE_HANDLER)
        manager.connect(SCRIPT_MESSAGE_RECEIVED_SIGNAL, self.on_js_message)
        self.configure_focus(self.config.focus)
        if self.config.inputMask:
            self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            self.connect("motion-notify-event", self.on_mouse_enter)

    def hide(self):
        """Hide the window."""
        self.view.hide()

    def show(self):
        """Show the window."""
        self.view.show()

    def on_mouse_enter(self, widget, event):
        """Handle mouse enter event."""
        if event.type != Gdk.EventType.ENTER_NOTIFY:
            return
        self.remove_input_mask()

    def on_js_message(self, manager, message):
        """Handle messages sent from JavaScript to the WebView."""

        data = message.get_js_value().to_string()
        print(f"Received JS message: {data}")
        try:
            data = json.loads(data)
            data = JSMessage(**data)
        except json.JSONDecodeError as e:
            log_exception(f"JSON decode error: {e}")
            return
        except ValidationError as e:
            log_exception(f"Validation error: {e}")
            return
        if data.name and data.name != self.name:
            return
        match data.type:
            case PayloadType.EXEC:
                if data.script:
                    log_info(f"Executing script: {data.script}")
                    run_detached_cmd(data.script)
            case PayloadType.MANUAL_STATE_UPDATE:
                handler = data.function
                if handler in self.manual_states:
                    if data.args is not None:
                        self.manual_states[handler](data.args)
                    else:
                        self.manual_states[handler]({})
                else:
                    log_warning(
                        f"Handler {handler} not found in manual states for widget:{self.name}"
                    )

            case PayloadType.CLOSE:
                # self.close()
                # self.widgets[widget_name].close()
                # self.base_webview.widgets[self.name].close()
                c = self.base_webview
                GLib.idle_add(c.widgets[self.name].close)
            case PayloadType.SYNC_DIMENSION:
                if data.width is not None and data.height is not None:
                    self.view.set_size_request(data.width, data.height)
            case PayloadType.INPUT_MASK:
                if data.masks is None:
                    data.masks = []
                res = [
                    # (int(x) - 15, int(y) - 15, int(w) + 15, int(h) + 15)
                    (int(x), int(y), int(w), int(h))
                    for x, y, w, h in data.masks
                ]
                self.input_mask = res
                if self.masking:
                    self.set_input_mask()

            case PayloadType.APPLY_INPUT_MASK:
                self.masking = True
                self.set_input_mask()
                log_info(f"Applied input mask: {self.input_mask}")
            case PayloadType.REMOVE_INPUT_MASK:
                self.masking = False
                self.remove_input_mask()
                log_info(f"Removed input mask: {self.input_mask}")
            case PayloadType.CONFIGURE_FOCUS:
                if data.focus is None:
                    log_error("Focus type is None, skipping configuration.")
                    return
                self.configure_focus(data.focus)
                log_info(f"Configured focus: {data.focus}")
            case PayloadType.CONFIGURE_GTK_LAYER_SHELL:
                self.configure_GTKLayerShell(data.config_layer)
                log_info(f"Configured GTK Layer Shell: {data.config_layer}")

    def after_load(self, view: WebKit2.WebView, load_event: WebKit2.LoadEvent):
        """Handle the load event of the WebView."""
        if load_event != WebKit2.LoadEvent.FINISHED:
            return
        self.execute_script(f"window.name = '{self.name}';")
        t = f"""window.weld= (o) =>{{
            window.webkit.messageHandlers.{SCRIPT_MESSAGE_HANDLER}.postMessage(
                JSON.stringify({{
                    ...o,
                    name: '{self.name}',
                }})
            );
        }};
        """
        self.execute_script(t)
        self.state_callback()
        if self.config.syncDimension:
            self.enable_dimension_sync()
        if self.config.inputMask:
            self.masking = True
            self.enable_input_masking()
        else:
            self.remove_input_mask()

    def configure_focus(self, type: str):
        match type:
            case FocusType.EXCLUSIVE:
                GtkLayerShell.set_keyboard_mode(
                    self, GtkLayerShell.KeyboardMode.EXCLUSIVE
                )
            case FocusType.ON_DEMAND:
                GtkLayerShell.set_keyboard_mode(
                    self, GtkLayerShell.KeyboardMode.ON_DEMAND
                )
            case FocusType.NONE:
                GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)

    def configure_GTKLayerShell(
        self, data: Optional[ConfigureGTKLayerShellPayloadData] = None
    ):
        """Configure GTK Layer Shell for the window."""
        """TODO: data typing"""

        if data is None:
            data = self.config
        GtkLayerShell.init_for_window(self)

        if data.layer:
            GtkLayerShell.set_layer(
                self,
                {
                    LayerType.BACKGROUND: GtkLayerShell.Layer.BACKGROUND,
                    LayerType.OVERLAY: GtkLayerShell.Layer.OVERLAY,
                    LayerType.TOP: GtkLayerShell.Layer.TOP,
                    LayerType.BOTTOM: GtkLayerShell.Layer.BOTTOM,
                }[data.layer],
            )
        edge_map = {
            AnchorType.TOP: GtkLayerShell.Edge.TOP,
            AnchorType.BOTTOM: GtkLayerShell.Edge.BOTTOM,
            AnchorType.LEFT: GtkLayerShell.Edge.LEFT,
            AnchorType.RIGHT: GtkLayerShell.Edge.RIGHT,
        }

        for anch in data.anchors:
            edge = edge_map[anch]
            GtkLayerShell.set_anchor(self, edge, True)

        margins = {
            GtkLayerShell.Edge.TOP: data.top,
            GtkLayerShell.Edge.BOTTOM: data.bottom,
            GtkLayerShell.Edge.LEFT: data.left,
            GtkLayerShell.Edge.RIGHT: data.right,
        }

        for edge, value in margins.items():
            if value is not None:
                GtkLayerShell.set_margin(self, edge, value)

        if data.reserved_space:
            GtkLayerShell.set_exclusive_zone(self, data.reserved_space)

    def enable_input_masking(self):
        """Enable input masking for the WebView."""
        self.execute_script(INPUT_MASK_JS)

    def enable_dimension_sync(self):
        """Enable dimension sync for the WebView."""
        self.execute_script(SYNC_DIMENSIONS_JS)

    def alert_frontend(self, message: str):
        """Send an alert message to the frontend."""
        script = f"""
        window.alert(`{message}`);
        """
        self.execute_script(script)

    def state_callback(self):
        for state in self.states:
            set_state = self.get_set_state(state.function)
            set_state("testing")
            match state.updateStrategy:
                case UpdateStrategy.INTERVAL:
                    if state.interval is None:
                        log_error(
                            f"Interval not set for {self.name} with update strategy INTERVAL"
                        )
                        continue
                    interval_mil = state.interval
                    interval_seconds = int(interval_mil / 1000)

                    def run():
                        # state.handler(run_cmd(state.script), set_state)
                        run_cmd_non_block(
                            state.script, lambda res: state.handler(res, set_state)
                        )

                    self.interval_runners.append(set_interval(run, interval_seconds))
                    log_info(
                        f"Set interval for {self.name}: {interval_seconds} seconds"
                    )
                case UpdateStrategy.ONCE:
                    # state.handler(run_cmd(state.script), set_state)
                    run_cmd_non_block(
                        state.script, lambda res: state.handler(res, set_state)
                    )
                case UpdateStrategy.CONTINOUS:

                    def output_callback(data):
                        state.handler(data, set_state)

                    self.processes.append(
                        run_continuous_cmd(state.script, output_callback)
                    )
                    log_info(f"Set continous for {self.name}: {state.script}")
                case UpdateStrategy.IPC:

                    def output_callback(data):
                        state.handler(data, set_state)

                    socket_path = state.script
                    self.processes.append(
                        run_unix_socket_threaded(socket_path, output_callback)
                    )
                    log_info(f"Set IPC (socket) for {self.name}: {socket_path}")
                case UpdateStrategy.DBUS:
                    log_info(
                        f"Set IPC (dbus) for {self.name}: {state.script} not implemented"
                    )
            if state.updateStrategy in [
                UpdateStrategy.MANUAL,
                UpdateStrategy.ONCE,
                UpdateStrategy.INTERVAL,
            ]:

                def state_callback(args: Optional[dict[str, str]] = {}):
                    s = state.script
                    for key, value in args.items():
                        s = s.replace(f"{{{key}}}", value)

                    run_cmd_non_block(s, lambda res: state.handler(res, set_state))

                self.manual_states[state.function] = state_callback

    def execute_script(self, script: str):
        """Execute a JavaScript script in the WebView."""
        self.view.evaluate_javascript(
            script=script,
            length=len(script),
            world_name=None,
            source_uri=None,
            cancellable=None,
            callback=None,
        )

    def set_input_mask(self):
        """Set the input mask for the window.
        Args:
            masks (list[tuple[int, int, int, int]]): List of masks where each mask is defined by (x, y, width, height).
        """
        import cairo

        region = cairo.Region()
        for mask in self.input_mask:
            x, y, w, h = mask
            region.union(cairo.RectangleInt(x, y, w, h))
        self.input_shape_combine_region(region)

    def remove_input_mask(self):
        """Remove the input shape from the window."""
        self.input_shape_combine_region(None)

    def set_window_transparency(self):
        """Set the window transparency."""
        self.set_app_paintable(True)
        self.view.set_background_color(Gdk.RGBA(0, 0, 0, 0))  # Transparent background

    def close(self, widget: Gtk.Widget = None):
        for cancel_runner in self.interval_runners:
            cancel_runner()
        for stop_process in self.processes:
            stop_process()
        for key in self.bindings:
            try:
                del self.base_webview.bindings[key]
            except KeyError:
                log_warning(f"Binding {key} not found in base_webview bindings.")
        self.base_webview.refresh_binds()
        self.destroy()
        log_debug(f"Destroying {self.name}")
        try:
            del self.base_webview.widgets[self.name]
        except KeyError:
            log_warning(
                f"Widget {self.name} not found in base_webview widgets. If you called close() manually, this is expected and known bug. If not, please check your code."
            )
        return False

    def get_set_state(self, function: str):
        """
        Get state updater function.
        Args:
            function (str): The name of the function to call.
        Returns:
            function: The function to call.
        """

        def state_updater(data: str):
            script = f"""
            window.{function}(`{data.strip()}`);
            """
            self.execute_script(script)

        return state_updater

    def bind_event(self, event: str):
        """
        Bind an event to the widget.
        Args:
            event (str): The name of the event to bind.
        """
        if self.name + event not in self.base_webview.bindings:
            return
        s = f"""
            if(window.name === '{self.name}')
            window.{event}();
            """
        self.execute_script(s)


class BaseWebView(Gtk.Window):
    view: WebKit2.WebView
    socket_path: str
    widgets: dict[str, WidgetWindow]

    def __init__(self):
        super().__init__(title="Base WebView")
        self.view = WebKit2.WebView()

        self.socket_path: str = SOCKET_PATH
        self._setup_ipc_socket()
        self.widgets = {}
        self.bindings = {}

    def refresh_binds(self):
        from weld.cli import PATH_TO_CLI
        from weld.Hyprlang import convert_code_to_hyprlang

        with open(WELD_BIND, "w") as f:
            t = "# Auto generated by weld\n"
            for key in self.bindings:
                widget = self.bindings[key]["widget"]
                function = self.bindings[key]["function"]
                bind_event = self.bindings[key]["bind_event"]
                t += f"bind = '{",".join(bind_event)}','exec','{PATH_TO_INTERPETER} {PATH_TO_CLI} send {widget} {function}'\n"

            f.write(convert_code_to_hyprlang(t))
        run_detached_cmd("hyprctl reload")

    def _setup_ipc_socket(self):
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.socket_path)
        self.socket.listen(1)
        self.socket.setblocking(False)
        GLib.io_add_watch(self.socket, GLib.IO_IN, self.handle_client_connection)

    def handle_client_connection(self, fd: int, condition: GLib.IOCondition):
        """GPT spit out this function and may have bugs."""
        if condition & GLib.IO_IN:
            try:
                client_socket, _ = self.socket.accept()
                data = client_socket.recv(4096)
                if data:
                    message = data.decode(TEXT_ENCODING)
                    log_info(f"Received message: {message}")
                    message = json.loads(message)
                    response = None  # Initialize response variable

                    match message["action"]:
                        case CliOptions.LIST:
                            widget_list = []
                            for f in os.listdir(WIDGET_DIR):
                                if os.path.isdir(
                                    os.path.join(WIDGET_DIR, f)
                                ) and os.path.exists(
                                    os.path.join(WIDGET_DIR, f, "config.py")
                                ):
                                    widget_list.append(f)
                            response = json.dumps(
                                {"status": "success", "data": widget_list}
                            )

                        case CliOptions.ADD:
                            widget_name = message["widget"]
                            if widget_name in self.widgets:
                                response = json.dumps(
                                    {
                                        "status": "error",
                                        "message": f"Widget {widget_name} already exists.",
                                    }
                                )
                            else:
                                widget_window = WidgetWindow(widget_name, self)
                                widget_window.show()
                                response = json.dumps(
                                    {
                                        "status": "success",
                                        "message": f"Widget {widget_name} added.",
                                    }
                                )

                        case CliOptions.REMOVE:
                            widget_name = message["widget"]
                            if widget_name in self.widgets:
                                self.widgets[widget_name].close()
                                response = json.dumps(
                                    {
                                        "status": "success",
                                        "message": f"Widget {widget_name} removed.",
                                    }
                                )
                            else:
                                response = json.dumps(
                                    {
                                        "status": "error",
                                        "message": f"Widget {widget_name} not found.",
                                    }
                                )

                        case CliOptions.RESTART:
                            widget_name = message["widget"]
                            if widget_name in self.widgets:
                                self.widgets[widget_name].close()
                            widget_window = WidgetWindow(widget_name, self)
                            widget_window.show()
                            response = json.dumps(
                                {
                                    "status": "success",
                                    "message": f"Widget {widget_name} restarted.",
                                }
                            )

                        case CliOptions.LIST_ACTIVE:
                            active_widgets = list(self.widgets.keys())
                            response = json.dumps(
                                {"status": "success", "data": active_widgets}
                            )

                        case CliOptions.SEND:
                            widget_name = message["widget"]
                            if widget_name in self.widgets:
                                self.widgets[widget_name].bind_event(
                                    message["bind_event"]
                                )

                                response = json.dumps(
                                    {"status": "success", "message": "OK"}
                                )
                            else:
                                response = json.dumps(
                                    {
                                        "status": "error",
                                        "message": f"Widget {widget_name} not found.",
                                    }
                                )

                    # Send the response back to the client
                    if response:
                        client_socket.send(response.encode(TEXT_ENCODING))

                client_socket.close()

            except Exception as e:
                error_response = json.dumps({"status": "error", "message": str(e)})
                client_socket.send(error_response.encode(TEXT_ENCODING))
                client_socket.close()
                log_exception(f"Error handling client connection: {e}")
        return True


__all__ = ["WidgetWindow", "BaseWebView"]
