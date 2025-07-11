from .core import BaseWebView, WidgetWindow
from .gi_modules import Gtk


def main():
    print("Starting Weld...")
    base_window = BaseWebView()
    Gtk.main()
