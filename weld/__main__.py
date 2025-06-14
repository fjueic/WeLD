
from weld.core import BaseWebView, WidgetWindow
from weld.gi_modules import Gtk



def main():
    print("Starting Weld...")
    base_window = BaseWebView()
    WidgetWindow("timenlauncher", base_window)
    # WidgetWindow("lock", base_window)
    Gtk.main()


if __name__ == "__main__":
    main()
