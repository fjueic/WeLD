import importlib.resources
import os
import shutil

from ..log import log_error, log_info


def _install_weld_sender():
    """
    Finds where 'weldctl' is installed (e.g., ~/.local/bin)
    and copies the 'weld-sender' binary to the same directory.

    I don't know of a better way to do this with pipx.
    """
    try:
        weldctl_exe_path = shutil.which("weldctl")
        if not weldctl_exe_path:
            log_error("'weldctl' executable not found on PATH. This shouldn't happen.")
            return False

        target_dir = os.path.dirname(weldctl_exe_path)
        target_sender_path = os.path.join(target_dir, "weld-sender")

        with importlib.resources.path("weld.bin", "weld-sender") as source_sender_path:

            log_info(f"Installing 'weld-sender' to {target_sender_path}...")
            shutil.copy(source_sender_path, target_sender_path)
            os.chmod(target_sender_path, 0o755)  # rwxr-xr-x
            log_info("'weld-sender' installed successfully.")
            return True

    except FileNotFoundError:
        log_error("CRITICAL: weld-sender binary not found in package. Re-install WeLD.")
    except Exception as e:
        log_error(f"Failed to auto-install 'weld-sender': {e}")

    return False


__all__ = ["_install_weld_sender"]
