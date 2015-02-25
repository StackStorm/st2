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
A trigger is a tuple of type (string) and optional parameters (object).
Rules are written to work with triggers. Sensors typically register triggers
though this is not strictly the case. For example, webhook triggers are just
registered independently. You don't have to write a sensor.

.. _ref-sensors-authoring-a-sensor:

Authoring a sensor
~~~~~~~~~~~~~~~~~~

Authoring a sensor involves authoring a python file and a yaml meta file
that defines the sensor. An example meta file is shown below.

.. literalinclude:: ../../contrib/examples/sensors/sample_sensor.yaml


Corresponding simple sensor python implementation is shown below.

.. literalinclude:: ../../contrib/examples/sensors/sample_sensor.py

It shows a bare minimum version of how a sensor would look like. Your
sensor should generate triggers of the form (python dict):

.. sourcecode:: python

    trigger = 'pack.name'
    payload = {
        'executed_at': '2014-08-01T00:00:00.000000Z'
    }

The sensor would inject such triggers by using the sensor\_service
passed into the sensor on instantiation.

.. code:: python

    self._sensor_service.dispatch(trigger=trigger, payload=payload)

If you want a sensor that polls an external system at regular intervals, you
would use a PollingSensor instead of Sensor as the base class.

.. literalinclude:: ../../contrib/examples/sensors/sample_polling_sensor.py

For a complete implementation of a sensor that actually injects triggers
into the system, look at the `examples <#Examples>`__ section.

Running your first sensor
~~~~~~~~~~~~~~~~~~~~~~~~~

Once you write your own sensor, the following steps can be used to run your sensor for the first time.

1. Place the sensor python file and yaml metadata in the 'default' pack in
/opt/stackstorm/packs/default/sensors/. Alternatively, you can create a
custom pack in /opt/stackstorm/packs/
with appropriate pack structure (see :doc:`/reference/packs`) and place the sensor artifacts there.

2. Register the sensor by using the st2ctl tool. Look out for any errors in sensor registration.

::

    st2ctl reload

If there are errors in registration, fix the errors and re-register them using st2ctl reload.

3. If registration is successful, you can run the sensor by restarting st2.

::

    st2 restart

Once you like your sensor, you can promote it to a pack (if required) by creating a pack in
/opt/stackstorm/packs/${pack_name} and moving the sensor artifacts (yaml and py) to
/opt/stackstorm/packs/${pack_name}/sensors/. See :doc:`/reference/packs` for how to create a pack.

Debugging a sensor from a pack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you just want to run a single sensor from a pack and the sensor is already registered, you can
use the sensor_container to run just that single sensor.

::

    sensor_container --config-file=conf/st2.conf --sensor-name=SensorClassName

For example:

::

    sensor_container --config-file=conf/st2.conf --sensor-name=GitCommitSensor

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

For more examples, please see sensors in the `st2contrib repo
<https://github.com/StackStorm/st2contrib/tree/master/packs>`__.
