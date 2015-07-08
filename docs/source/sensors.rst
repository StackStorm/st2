Triggers and Sensors
=====================

Sensors
-------

Sensors are essentially adapters that are a way to integrate |st2|
with an external system so that triggers can be injected into |st2|
before rule matching results in potential actions. Sensors are pieces
of Python code and have to follow the |st2| defined sensor interface
requirements to be successfully run.

Triggers
--------

Triggers are |st2| constructs that identify the incoming events to |st2|.
A trigger is a tuple of type (string) and optional parameters (object).
Rules are written to work with triggers. Sensors typically register triggers
though this is not strictly the case. For example, webhook triggers are just
registered independently. You don't have to write a sensor.

Internal triggers
-----------------

By default StackStorm emits some internal triggers which you can leverage in the
rules. Those triggers can be distinguished by non-system triggers since they are
prefixed with ``st2.``.

A list of available triggers for each resource is included below.

.. include:: _includes/internal_trigger_types.rst

.. _ref-sensors-authoring-a-sensor:

Authoring a sensor
------------------

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
into the system, look at the `examples <#examples>`__ section.

Sensor service
--------------

As you can see in the example above, a ``sensor_service`` is passed to each
sensor class constructor on instantiation.

Sensor service provides different services to the sensor via public methods.
The most important one is the ``dispatch`` method which allows sensors to inject
triggers into the system.

All public methods are described below.

Common operations
-----------------

1. dispatch(trigger, payload)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method allows sensor to inject triggers into the system.

For example:

.. code:: python

    trigger = 'pack.name'
    payload = {
        'executed_at': '2014-08-01T00:00:00.000000Z'
    }

    self._sensor_service.dispatch(trigger=trigger, payload=payload)

2. get_logger(name)
~~~~~~~~~~~~~~~~~~~

This method allows sensor instance to retrieve logger instance which is specific
to that sensor.

For example:

.. code:: python

    self._logger = self._sensor_service.get_logger(name=self.__class__.__name__)
    self._logger.debug('Polling 3rd party system for information')

Datastore management operations
-------------------------------

In addition to the trigger injection, sensor service also provides
functionality for reading and manipulating the :doc:`datastore <datastore>`.

Each sensor has a namespace which is local to it and by default, all the
datastore operations operate on the keys in that sensor-local namespace.
If you want to operate on a global namespace, you need to pass ``local=False``
argument to the datastore manipulation method.

Among other reasons, this functionality is useful if you want to persist
temporary data between sensor runs.

A good example of this functionality in action is ``TwitterSensor``. Twitter
sensor persist the id of the last processed tweet after every poll in the
datastore. This way if the sensor is restarted or if it crashes, the sensor
can resume from where it left off without injecting duplicated triggers into
the system.

For implementation, see the following page - https://github.com/StackStorm/st2contrib/blob/master/packs/twitter/sensors/twitter_search_sensor.py#L56

1. list_values(local=True, prefix=None)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method allows you to list the values in the datastore. You can also filter
by key name prefix (key name starts with) by passing ``prefix`` argument to the
method.

For example:

.. code:: python

    kvps = self._sensor_service.list_values(local=False, prefix='cmdb.')

    for kvp in kvps:
        print(kvp.name)
        print(kvp.value)

2. get_value(name, local=True)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method allows you to retrieve a single value from the datastore.

For example:

.. code:: python

    kvp = self._sensor_service.get_value('cmdb.api_host')
    print(kvp.name)

3. set_value(name, value, ttl=None, local=True)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method allows you to store (set) a value in the datastore. Optionally you
can also specify time to live (TTL) for the stored value.

.. code:: python

    last_id = 12345
    self._sensor_service.set_value(name='last_id', value=str(last_id))

4. delete_value(name, local=True)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method allows you to delete an existing value from a datastore. If a value
is not found this method will return ``False``, ``True`` otherwise.

.. code:: python

    self._sensor_service.delete_value(name='my_key')

API Docs
~~~~~~~~

.. autoclass:: st2reactor.container.sensor_wrapper.SensorService
    :members:

Running your first sensor
-------------------------

Once you write your own sensor, the following steps can be used to run your sensor for the first time.

1. Place the sensor python file and yaml metadata in the 'default' pack in
/opt/stackstorm/packs/default/sensors/. Alternatively, you can create a
custom pack in /opt/stackstorm/packs/
with appropriate pack structure (see :doc:`/reference/packs`) and place the sensor artifacts there.

2. Register the sensor by using the st2ctl tool. Look out for any errors in sensor registration.

::

    st2ctl reload

If there are errors in registration, fix the errors and re-register them using st2ctl reload.

3. If registration is successful, the sensor would be automatically run.


Once you like your sensor, you can promote it to a pack (if required) by creating a pack in
/opt/stackstorm/packs/${pack_name} and moving the sensor artifacts (yaml and py) to
/opt/stackstorm/packs/${pack_name}/sensors/. See :doc:`/reference/packs` for how to create a pack.

Debugging a sensor from a pack
------------------------------

If you just want to run a single sensor from a pack and the sensor is already registered, you can
use the st2sensorcontainer to run just that single sensor.

::

    st2sensorcontainer --config-file=/etc/st2/st2.conf --sensor-ref=pack.SensorClassName

For example:

::

    st2sensorcontainer --config-file=/etc/st2/st2.conf --sensor-ref=git.GitCommitSensor

Examples
--------

For more examples, please reference packs in the `st2contrib repo
<https://github.com/StackStorm/st2contrib/tree/master/packs>`__.
