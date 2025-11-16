# AstalBatteryService

The `AstalBatteryService` provides real-time battery information from your system. It uses the Astal library (which wraps upowerd) to get its data.

This service is subscription-based. It will only connect to and listen for the specific battery properties (like "percentage" or "state") that you request in your configuration. Entire list is in example.

Widget Configuration

To use the service, you must add it to your states list and provide a service_arguments dictionary.

- event: The event name to listen for in your JavaScript (e.g., "battery" will emit "weld:battery" events).

- updateStrategy: Must be UpdateStrategy.SERVICE.

- service_factory: Must be AstalBatteryService.

- service_arguments: A dictionary containing:

    - thingsToWatch: A list of strings specifying which properties you want to subscribe to.

For force a refresh, a handler is available:
```
window.weld({
    type: "manual_state_update",
    event: "AstalBattery:sync"
});
```


