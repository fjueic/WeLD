import os
import subprocess

from setuptools import setup
from setuptools.command.build_py import build_py

C_SOURCE = "weld/c/weld-sender.c"
BINARY_NAME = "weld-sender"
OUTPUT_PATH = f"weld/bin/{BINARY_NAME}"


class BuildCExec(build_py):
    def run(self):
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

        super().run()


setup(
    cmdclass={'build_py': BuildCExec},
)
