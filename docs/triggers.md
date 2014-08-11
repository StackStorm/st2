Creating triggers should be done via the API. Unfortunately, this API isn't complete. So until that happens, you'll need to go through these manual steps
to setup timers and webhooks.

## Configuring timers

1. Edit [config file](../st2reactor/st2reactor/contrib/sensors/st2_timer_sensor.yaml) and add a new named timer trigger. For example,
    timer.mytimer:
    type: interval
    timezone: utc
    time:
        delta: 30
        unit: seconds

2. Use these named timer triggers in your rule [Refer rule section],

        ./rule.json:
        { "name": "mytimerrule",
        "trigger": {
            "name": "timer.mytimer"
        ...
   Note that you are referring to the trigger by name "timer.mytimer" which was
   supplied in the config. Stanley basically registered the trigger for you under the hood.

3. Reboot stanley to pick the config and the rule:
   ```
    ${SRC_ROOT}/tools/launchdev.sh stop
    ${SRC_ROOT}/tools/launchdev.sh start
   ```
Note: You cannot emit custom payloads on a pre-defined timer. For this, you'd need to write your own sensor. See [sensors](sesnors.md) section.

## Configuring Webhooks

1. Edit [config file](../st2reactor/st2reactor/contrib/sensors/st2_generic_webhook_sensor.yaml) and add a string there. This string will serve both as a name of the webhook trigger and a subpath to the url. For example, call it "mywebhook". 
This will spin up an endpoint ```http://{host}:6001/webhooks/generic/mywebhook```.

2. Register the webhook trigger, named "mywebhook".
   Create a json file mywebhooktrigger.json (file name can be anything)

        ./mywebhooktrigger.json
        {
            "name": "mywebhook",
            "description": "call it yourname.webhooktrigger",
            "payload_schema": {}
        }
    Use st2 cli to register this trigger.
    $st2 trigger create -j mywebhooktrigger.json
    Note: In this case, stanley did not auto register the trigger type for you. Since you can specify the payload schema for the webhook if you know,
    this manual step is required now.

3. Create a rule.json for that trigger:
   
        ./rule.json:
        { "name": "mywebhookrule",
            "trigger": {
            "name": "webhooks.mywebhook"

4. Reboot Stanley: 
    ```
      ${SRC_ROOT}/tools/launchdev.sh stop  
      ${SRC_ROOT}/tools/launchdev.sh start
    ```
5. Use curl or [httpie](https://github.com/jakubroztocil/httpie) to POST aribitrary payload to the endpoint. An example using httpie is shown below.
```
http POST http://{host}:6001/webhooks/generic/mywebhook < payload.json
```
  Example payload:
  ```json
    { 
      "foo": "bar",
      "baz": 1
    }
  ```

## API status
* Partially complete. [Look out for alpha.]
* You can create simple triggers without parameters using the API.

## CLI status
* Mirrors APIs. Try out:
```
st2 trigger list|create|get|delete
```
