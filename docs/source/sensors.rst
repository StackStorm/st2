Triggers and Sensors
=====================

Sensors
~~~~~~~~

Sensors are essentially adapters that are a way to integrate |st2|
with an external system so that triggers can be injected into |st2|
before rule matching results in potential actions. Sensors are pieces
of Python code and have to follow the |st2| defined sensor interface
requirements to be successfully run.

Triggers
~~~~~~~~

Triggers are |st2| constructs that identify the incoming events to |st2|.
A trigger is a tuple of type (string) and optional parameters (object). Rules are written to work with triggers. Sensors typically register triggers though this is not strictly the case. For example, webhook triggers are just registered independently. You don't have to write a sensor.

.. _ref-sensors-authoring-a-sensor:

Authoring a sensor
~~~~~~~~~~~~~~~~~~

A simple sensor implementation is shown below.

.. literalinclude:: ../../contrib/examples/sensors/sample_sensor.py


It shows a bare minimum version of how a sensor would look like. Your
sensor should generate triggers of the form (python dict):

::

    {
        'name': 'name of the trigger you register in get_trigger_types() method. required.',
        'pack': 'pack that contains this sensor',
        'payload' : { # required field. contents can be empty.
            'foo': 'bar',
            'baz': 1,
            'time': '2014-08-01T00:00:00.000000Z'
        }
    }

The sensor would inject such triggers by using the sensor\_service
passed into the sensor on instantiation.

.. code:: python

    self._service.dispatch(trigger, payload)

If you want a sensor that polls an external system at regular intervals, you
would use a PollingSensor instead of Sensor as the base class.

.. literalinclude:: ../../contrib/examples/sensors/sample_polling_sensor.py

For a complete implementation of a sensor that actually injects triggers
into the system, look at the `examples <#Examples>`__ section.

Once you write your own sensor, you can test it stand alone like so:

::

    st2reactor/bin/sensor_container --config-file=conf/st2.conf --sensor-path /path/to/sensor/file

[Note: You should have setup the virtualenv and activated it before the
previous command can work.]

If you are happy about your sensor and you want the system to always run it, place your sensor in a pack you choose /opt/stackstorm/packs/${pack_name}/sensors/.

::

    $cp /path/to/sensor/${sensorfile}.py /opt/stackstorm/packs/${pack_name}/sensors/${sensorfile}.py

Note: If |st2| reactor component is already running on the box, you'll
have to restart it to pick up the new sensor.

Examples
~~~~~~~~

EC2 health check sensor
^^^^^^^^^^^^^^^^^^^^^^^

This `EC2
sensor <https://github.com/StackStorm/st2contrib/blob/master/packs/aws/sensors/ec2instancestatussensor.py>`_ uses
boto library to talk to AWS and emits the health of instances as
triggers.

Advanced examples
~~~~~~~~~~~~~~~~~

There are some common use cases that we identified and |st2| comes
bundled with some default sensors. For example, the two triggers in
this section are implemented as sensors.

Timer sensor
^^^^^^^^^^^^

Look at the timer sensor implementation
`here <https://github.com/StackStorm/st2/blob/master/st2reactor/st2reactor/contrib/sensors/st2_timer_sensor.py>`__.
Timer uses `APScheduler <http://apscheduler.readthedocs.org/en/3.0/>`__
as the scheduling engine.

More sensor examples are in
`st2contrib repo <https://github.com/StackStorm/st2contrib/tree/master/packs>`__.
