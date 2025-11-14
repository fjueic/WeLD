import argparse
import json
import os
import socket
import sys

from weld.c.install import _install_weld_sender
from weld.constants import SOCKET_PATH, TEXT_ENCODING
from weld.type.cli import CliOptions

PATH_TO_CLI = os.path.abspath(__file__)

# Path to the socket where WeLD service is listening


def send_command(action, widget_name=None, bind_event=None):
    """Send a command to the WeLD service and return the response."""
    command = {"action": action, "widget": widget_name}
    if bind_event is not None:
        command["bind_event"] = bind_event

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(SOCKET_PATH)
        client.send(json.dumps(command).encode(TEXT_ENCODING))

        # Wait for and receive the response
        response = client.recv(4096)
        if response:
            return json.loads(response.decode(TEXT_ENCODING))
        return None


def main():
    parser = argparse.ArgumentParser(description="WeLD CLI Tool")
    parser.add_argument(
        "action",
        choices=[enum.value for enum in CliOptions],
        help="Action to perform on the widget",
    )
    parser.add_argument(
        "widget",
        nargs="?",
        help="Name of the widget to perform the action on (not needed for 'list')",
    )
    parser.add_argument(
        "bind_event",
        nargs="?",
        help="Additional data to send with the command (optional)",
    )

    args = parser.parse_args()

    if args.action == CliOptions.INSTALL_SENDER:
        if _install_weld_sender():
            print("weld-sender installed successfully.")
            sys.exit(0)
        else:
            print("Failed to install weld-sender.", file=sys.stderr)
            sys.exit(1)

    if args.action not in ["list", "listactive"] and not args.widget:
        parser.error(f"The '{args.action}' action requires a widget name.")

    response = send_command(args.action, args.widget, args.bind_event)

    if response:
        if response["status"] == "error":
            print(response["message"], file=sys.stderr)
            print(f"Error: {response['message']}", file=sys.stderr)
            sys.exit(1)
        else:
            if "data" in response:
                # For list commands, print each item on a new line
                if isinstance(response["data"], list):
                    print("\n".join(response["data"]))
                else:
                    print(response["data"])
            elif "message" in response:
                print(response["message"])
    else:
        print("No response received from server", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":

    main()
