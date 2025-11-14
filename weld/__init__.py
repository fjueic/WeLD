import signal

from .core.widget import BaseWebView  # Assuming this is your BaseWebView import
from .gi_modules import GLib, Gtk
from .log import log_info


def shutdown_handler(base_view_instance):
    log_info("Shutdown signal received. Cleaning up widgets...")
    for widget in list(base_view_instance.widgets.values()):
        widget.close()

    Gtk.main_quit()

    return GLib.SOURCE_REMOVE


def main():
    log_info("Starting WeLD...")
    base_view = BaseWebView()
    GLib.unix_signal_add(
        GLib.PRIORITY_DEFAULT, signal.SIGINT, shutdown_handler, base_view
    )
    Gtk.main()
    log_info("WeLD has shut down.")


if __name__ == "__main__":
    main()
