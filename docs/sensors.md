## Sensors

### What?

Sensors are essentially adapters that are a way to integrate stanley with an external system so that triggers can be injected into stanley before rule matching results in potential actions. Sensors are a piece of Python code and have to follow the stanley defined sensor interface requirements to be
successfully run.

### How? (a.k.a writing your own sensor)

For a simple sensor, review [contrib/examples/sensors/sample_sensor.py](../contrib/examples/sensors/sample_sensor.py). It shows a bare minimum version of how a sensor would look like. Your sensor should generate triggers of the form (python dict):
```
{
    'name': 'name of the trigger you register in get_trigger_types() method. required.'
    'event_id': 'optional event_id field to associate this to an external event'
    'payload' : { # required field. contents can be empty.
        'foo': 'bar',
        'baz': 1,
        'time': '2014-08-01T00:00:00.000000Z'
    }
}
```
The sensor would inject such triggers by using the container_service passed into the sensor on instantiation.
```python
self._container_service.dispatch(triggers)
```
For a complete implementation of a sensor that actually injects triggers into the system, look at the [examples](#Examples) section.

Once you write your own sensor, you can test it stand alone like so:
```
st2reactor/bin/sensor_container --config-file=conf/stanley.conf --sensor-path /path/to/sensor/file
```
[Note: You should have setup the virtualenv and activated it before the previous command can work.]

If you are happy about your sensor and you want the system to always run it, place your sensor in
/opt/stackstorm/sensors/.
```
$cp /path/to/sensor/${sensorfile}.py /opt/stackstorm/sensors/
```
Note: If stanley reactor component is already running on the box, you'll have to restart it to pick up the new sensor.

### Examples

#### EC2 health check sensor:
This [EC2 sensor](../contrib/sandbox/packages/aws/sensors/ec2sensor.py) uses
boto library to talk to AWS and emits the health of instances as triggers. 

### Advanced examples

There are some common use cases that we identified and stanley comes bundled with some default sensors. For example, the two triggers in [triggers](triggers.md) section are implemented as sensors.

#### Timer sensor

Look at the timer sensor implementation [here](../st2reactor/st2reactor/contrib/sensors/st2_timer_sensor.py). It relies on a [config](../st2reactor/st2reactor/contrib/sensors/st2_timer_sensor.yaml) to get user configuration. Timer uses
[APScheduler](http://apscheduler.readthedocs.org/en/3.0/) as the scheduling
engine.

#### Generic Webhook sensor 

Look at the generic webhooks sensor implementation [here](../st2reactor/st2reactor/contrib/sensors/st2_generic_webhook_sensor.py). It relies on a [config](../st2reactor/st2reactor/contrib/sensors/st2_generic_webhook_sensor.yaml) for user configuration. The payload here can have arbitray structure.
The webhook sensor uses [Flask](http://flask.pocoo.org/) to spin up restful
endpoints.

#### Stanley webhook sensor

Stanley defines it's own webhook format if you want a REST interface to inject triggers from curl or other plugins. Unlike the generic webhooks, the payload for this endpoint should be in a form stanley expects. Look at the sensor implementation [here](..//st2reactor/st2reactor/contrib/sensors/st2_webhook_sensor.py). The payload format is
```json
    {
        "name":"name.of.the.trigger.you.registered.",
        "payload_info": {"key1", "key2", "key3"}        
    }
```

More sensor examples are in [contrib/sandbox/packages](../contrib/sandbox/packages/).

## API status

* Non-existent. [Look out for alpha]

## CLI status
* Non-existent. [Look out for alpha]
