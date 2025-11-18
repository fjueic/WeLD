# WeLD Service: AstalAuthService

The `AstalAuthService` provides a simple and secure way to authenticate the user using PAM (Pluggable Authentication Modules). This is the standard authentication system on Linux.

This service is "conversational." It will send messages to your widget (like "show password prompt") and then wait for your widget to send a reply (the password).

## Configuration (`config.py`)

To use the service, add it to your `states` list in your widget's `config.py`.

* **`event`**: The event name to listen for in your JavaScript (e.g., `"auth"`).
* **`updateStrategy`**: Must be `UpdateStrategy.SERVICE`.
* **`service_factory`**: Must be `AstalAuthService`.
* **`service_arguments`**: A dictionary to configure the PAM service.
    * **`service` (str)**: The PAM service to use.
        * `"polkit-1"`: The standard for GUI applications.

### Example `config.py`

This config sets up the service to authenticate the current user for `polkit-1`, which is the standard for desktop actions, username can be passed in `service_arguments`.


Sending Commands to the Service

You send commands using window.weld().
| Command       | window.weld(...)                                                                                     | Description                          |
|---------------|--------------------------------------------------------------------------------------------------------|--------------------------------------|
| Start         | window.weld({ type: "manual_state_update", event: "AstalAuth:start", args: {} })                           | Begins the authentication flow.      |
| Send Secret   | window.weld({ type: "manual_state_update", event: "AstalAuth:secret", args: { "secret": "..." } })         | Sends the password (or other text) to PAM. |
| Cancel        | window.weld({ type: "manual_state_update", event: "AstalAuth:cancel", args: {} })                          | Aborts the authentication flow.      |


# Listening to the Service

You listen for events on the event name you defined in your config (e.g., "weld:auth"). The service will send a JSON object in event.detail:

event.detail = { "status": "...", "message": "..." }

| Status        | Message                     | Meaning                                             |
|---------------|-----------------------------|-----------------------------------------------------|
| prompt_hidden | """Password: """            | Show a password field. (<input type="password">)   |
| prompt_visible| """Username: """            | Show a text field. (<input type="text">)           |
| success       | """Authentication Succeeded""" | Auth passed. Hide the prompt.                    |
| fail          | """Authentication Failed""" | Wrong password. Hide the prompt.                   |
| error         | """PAM module error"""      | A system error occurred.                            |
| info          | """Authenticating..."""     | A simple informational message.                     |


