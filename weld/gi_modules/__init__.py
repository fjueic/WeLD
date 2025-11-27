import gi

# Declare all versions before importing
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Gdk", "3.0")
gi.require_version("Gio", "2.0")
gi.require_version("GObject", "2.0")
gi.require_version("Soup", "3.0")

from gi.repository import Gdk, Gio, GLib, GObject, Gtk, GtkLayerShell, Soup, WebKit2

__all__ = ["Gdk", "GLib", "Gtk", "GtkLayerShell", "WebKit2", "Gio", "GObject", "Soup"]
