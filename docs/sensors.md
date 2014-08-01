Sensors
=======

What?
=====

Sensors are essentially adapters that are a way to integrate stanley with an external system so that
triggers can be injected into stanley before rule matching results in potential actions. Sensors
are a piece of Python code and have to follow the stanley defined sensor interface requirements to be
successfully run.

How?
====

For a simple sensor, look here: ```${SRC_ROOT}/contrib/examples/sensors/sample_sensor.py```. It shows
a bare minimum version of how a sensor would look like.

Your sensor should generate triggers of the form (python dict):
{
    'name': 'name of the trigger you register in get_trigger_types() method. required.'
    'event_id': 'optional event_id field to associate this to an external event'
    'payload' : { # required field. contents can be empty.
        'foo': 'bar',
        'baz': 1,
        'time': '2014-08-01T00:00:00.000000Z'
    }
}
The sensor would inject such triggers by using the container_service passed into the sensor on
instantiation.
self._container_service.dispatch(triggers)

For a complete implementation of a sensor that actually injects triggers into the system, look here:
${SRC_ROOT}/st2reactor/contrib/sensors/st2_generic_webhook_sensor.py. It is a flask app that listens
on endpoints specified in config file. Any POST to those endpoints will kickoff triggers with
the webhook body passed in as payload for triggers.

Once you write your own sensor, you can test it stand alone like so:
st2reactor/bin/sensor_container --config-file=conf/stanley.conf --sensor-path /path/to/sensor/file

[Note: You should have setup the virtualenv and activated it before the previous command can work.]

If you are happy about your sensor and you want the system to always run it, place your sensor in
/opt/stackstorm/sensors/.
Note: If stanley reactor component is already running on the box, you'll have to hup it to pick up
the new sensor.

Pre-defined sensors:
====================

There are some common use-cases that we identified and stanley comes bundled with some default
sensors. There are two kinds currently:
1. Timers.
2. Webhooks.

Ideally, we'd like to be in a state where you just configure these via an API endpoint. For now,
you'd have to go through these manual steps to configuring them:


Configuring timer sensors:
==========================

1. Edit ${SRC_ROOT}/st2reactor/st2reactor/contrib/sensors/st2_timer_sensor.yaml, create a new
   named timer trigger. For example,
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

3. Reboot stanley to pick the config and the rule:
    $${SRC_ROOT}/tools/launch.sh stop
    $${SRC_ROOT}/tools/launch.sh start

Note: You cannot emit custom payloads on a pre-defined timer. For this, you'd need to write your
own sensor.

Configuring Webhooks:
=====================

1. Edit ```${SRC_ROOT}/st2reactor/st2reactor/contrib/sensors/st2_generic_webhook_sensor.yaml.```
   Add a string there. This string will serve both as a name of the webhook trigger,
   and a subpath to the url. For example, call it "mywebhook". This will spin up an endpoint
   ```http://{host}:6001/webhooks/generic/mywebhook```

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

3. Create a rule.json for that trigger:
   
        ./rule.json:
        { "name": "mywebhookrule",
            "trigger": {
            "name": "webhooks.mywebhook"

4. Reboot Stanley: tools/launch.sh stop  tools/launch.sh start

5. Use curl or httpie [https://github.com/jakubroztocil/httpie] to POST aribitrary payload to the
   endpoint: ```http://{host}:6001/webhooks/generic/mywebhook```
   Please avoid obscure tools like curl.
