:orphan:

Pack Testing
============

This section includes information on pack testing - where to put the tests,
how to write the tests, mock classes which can be used to make testing
easier, etc.

Test File Locations and Names
-----------------------------

All the test files should go into ``<pack name>/tests/`` directory. If tests
include any fixtures, they should be put in the ``<pack name>/tests/fixtures/``
directory.

Test files should follow the following naming conventions:

* ``test_action_<action name>.py`` for action tests. For example, if the action
  is named ``parse_xml``, the file should be named
  ``test_action_parse_xml.py``.
* ``test_sensor_<sensor name>.py`` for sensor tests. For example, if the sensor
  is named ``GithubEvents``, the file should be named
  ``test_sensor_github_events.py``.

General Testing Conventions
---------------------------

Most of the |st2| packs interact with a third party API or tool. Writing
full blown integration and end to end tests would be very time consuming and
hard so the convention is to write unit tests and mock the responses and method
calls where necessary.

Mock Classes
------------

To make testing easier, |st2| provides some mock classes which you can use
in the tests.

* ``st2tests.mocks.runner.MockActionRunner`` - Mock action runner class which
  allows you to specify a mock status, result and context which is returned
  from the ``run`` method.
* ``st2tests.mocks.sensor.MockSensorWrapper`` - Mock ``SensorWrapper`` class.
* ``st2tests.mocks.sensor.MockSensorService`` - Mock ``SensorService`` class.
  This class mock methods which operate on the datastore items (``list_values``,
  ``get_value``, ``set_value``, ``delete_value``).

In addition to the mock classes, |st2| also provides base class for sensor
tests - ``st2tests.base.BaseSensorTestCase``. This class provides utility
functions for making sensor testing easier such as returning a sensor class
instance with ``sensor_service`` correctly populated, method for asserting
that trigger has been dispatched (``assertTriggerDispatched``) and more.

Dependencies
------------

In addition to all the |st2| and pack dependencies listed in
``requirements.txt`` and ``requirements-tests.txt``, the following libraries are
also available by default inside the tests:

* ``unittest2``
* ``mock``

In addition those dependencies, sensors (``<pack name>/sensors/``) and actions
(``<pack name>/actions/``) directory is added to PYTHONPATH meaning you can import
sensor and action modules directly in your code.

For example, if you have an action named ``actions/parse_xml.py`` you can do the
following inside your test module:

```python
import parse_xml
```

Keep in mind that both sensor and action modules are not namespaced which means
sensor and action module names need to be unique to avoid conflicts.

Running Tests
-------------

To run all the tests in a particular pack you can use the ``run-pack-tests.sh``
script from the ``st2contrib`` repository as shown below.

```bash
./scripts/run-pack-tests.sh <pack path>
```

For example:

```bash
./scripts/run-pack-tests.sh packs/example
```

Continous Integration
---------------------

By default tests for all the packs are ran on every commit to ``st2contrib``
repository.
