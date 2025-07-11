import socket
import subprocess
import threading
from typing import Callable

from ..gi_modules import GLib, Gtk, WebKit2

from ..constants import SOCKET_PATH, TEXT_ENCODING


def run_cmd_non_block(cmd: str, callback: Callable[[str], None]) -> None:
    """Run a command asynchronously and call the callback with output."""

    def task():
        try:
            result = subprocess.run(
                cmd, shell=True, check=True, capture_output=True, text=True
            )
            output = result.stdout
        except subprocess.CalledProcessError as e:
            output = f"Error: {e.stderr}"

        GLib.idle_add(callback, output)

    threading.Thread(target=task, daemon=True).start()


def set_interval(func, interval_seconds):
    """Run `func` every `interval_seconds` seconds using GLib's main loop.

    Returns:
        A function to cancel the interval.
    """

    def wrapper():
        func()  # Execute the function
        return True  # Return True to keep the timer active

    # Register the timeout
    source_id = GLib.timeout_add_seconds(interval_seconds, wrapper)

    # Return a function to cancel the interval
    def cancel():
        GLib.source_remove(source_id)

    return cancel


def run_cmd(cmd: str) -> str:
    """Run a command in the shell.
    Args:
        cmd (str): The command to run.
    Returns:
        str: The output of the command. Result or error message.
    """
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"


def run_continuous_cmd(cmd: str, callback):
    """Run command in background thread and stream output line-by-line."""

    process = None

    def worker():
        nonlocal process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            text=True,
            bufsize=1,
        )

        # Reading lines from the process
        for line in process.stdout:
            GLib.idle_add(callback, line.strip())

        # Wait for process to exit
        process.stdout.close()
        process.wait()

        # Notify callback of exit
        GLib.idle_add(callback, f"[Process exited with code {process.returncode}]")

    def stop():
        """Stop the process and clean up."""
        if process:
            process.terminate()  # Send SIGTERM to gracefully terminate the process
            process.wait()  # Ensure process is fully terminated
            print("Process terminated.")

    # Start the worker thread
    threading.Thread(target=worker, daemon=True).start()

    return stop


def run_unix_socket_threaded(socket_path, callback):
    """Connect to a UNIX domain socket and read messages in a background thread."""
    stop_event = threading.Event()

    def worker():
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(socket_path)
            sock_file = sock.makefile("r")  # Line-buffered reading

            while not stop_event.is_set():
                line = sock_file.readline()
                if not line:
                    break
                GLib.idle_add(callback, line.strip())

        except Exception as e:
            GLib.idle_add(callback, f"[Socket error: {e}]")
        finally:
            try:
                sock_file.close()
                sock.close()
            except:
                pass
            GLib.idle_add(callback, "[Socket closed]")

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    def stop():
        stop_event.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            GLib.idle_add(callback, f"[Socket shutdown error: {e}]")

    return stop


def run_detached_cmd(cmd: str):
    """Run a command in the background, fully detached from the parent process.

    Args:
        cmd (str): The command to run.
    Returns:
        bool: True if process started successfully, False otherwise.
    """
    try:
        # On Unix, start new session and redirect file descriptors
        subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
        )
        return True
    except Exception as e:
        print(f"Failed to run detached command: {e}")
        return False


__all__ = [
    "set_interval",
    "run_cmd",
    "run_continuous_cmd",
    "run_unix_socket_threaded",
    "run_detached_cmd",
    "run_cmd_non_block",
]
