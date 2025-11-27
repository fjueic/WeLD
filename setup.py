import os
import subprocess
import sys
import sysconfig

from setuptools import setup
from setuptools.command.build_py import build_py

C_SOURCE = "weld/c/weld-sender.c"
BINARY_NAME = "weld-sender"
OUTPUT_PATH = f"weld/bin/{BINARY_NAME}"
PURELIB_DIR = os.path.abspath(sysconfig.get_paths()["purelib"])

IS_DEV_MODE = "editable_wheel" in sys.argv


class BuildCExec(build_py):
    def compile_c_exec(self):
        print(f"Compiling {C_SOURCE} -> {OUTPUT_PATH}")
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

        compile_command = [
            "gcc",
            C_SOURCE,
            "-o",
            OUTPUT_PATH,
            "-O3",
            "-Wall",
        ]
        try:
            subprocess.run(compile_command, check=True)
            print(f"Successfully compiled {BINARY_NAME}")
        except Exception as e:
            print(f"ERROR: Failed to compile {BINARY_NAME}. Do you have gcc?")
            raise e

    def add_symbolic_link(self):
        sym_links = [
            "Gdk.pyi",
            "GLib.pyi",
            "Gtk.pyi",
            "Gio.pyi",
            # "GtkLayerShell.pyi",
            # "WebKit.pyi",
        ]

        project_root = os.path.dirname(os.path.abspath(__file__))

        from_dir = os.path.join(PURELIB_DIR, "gi-stubs", "repository")
        to_dir = os.path.join(project_root, "weld", "gi-stubs", "gi", "repository")

        for sym_link in sym_links:

            source_path = os.path.join(from_dir, sym_link)
            link_path = os.path.join(to_dir, sym_link)
            relative_source_path = os.path.relpath(source_path, start=to_dir)

            if os.path.lexists(link_path):
                if os.path.islink(link_path) or os.path.isfile(link_path):
                    os.remove(link_path)
                elif os.path.isdir(link_path):
                    os.rmdir(link_path)

            try:
                os.symlink(relative_source_path, link_path)
            except Exception as e:
                raise

    def run(self):
        self.compile_c_exec()
        if IS_DEV_MODE:
            self.add_symbolic_link()

        super().run()


setup(
    cmdclass={
        'build_py': BuildCExec,
    },
)
