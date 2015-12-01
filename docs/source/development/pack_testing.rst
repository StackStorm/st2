:orphan:

Pack Testing
============

This section includes information on pack testing - where to put the tests,
how to write the tests, mock classes which can be used to make testing
easier, etc.

Test Files Locations
-------------------

Packs should follow the test file location conventions as outlined below.

* ``<pack name>/tests/`` - global tests (tests which are not specific to sensors
  or actions).
* ``<pack name>/sensors/tests/`` - sensor specific tests
* ``<pack name>/actions/tests/`` - action specific tests

If tests include any fixtures, they should be put in the ``tests/fixtures/``
directory as shown below.

* ``<pack name>/tests/fixtures/``
* ``<pack name>/sensors/tests/fixtures/``
* ``<pack name>/actions/tests/fixtures/``

General Testing Conventions
---------------------------

Most of the StackStorm packs interact with a third party API or tool. Writing
full blown integration and end to end tests would be very time consuming and
hard so the convention is to write unit tests and mock the responses and method
calls where necessary.

Mock Classes
------------

To make testing easier, StackStorm provides some mock classes which you can use
in the tests.

* ``st2tests.mocks.runner.MockActionRunner`` - Mock action runner class which
  allows you to specify a mock status, result and context which is returned
  from the ``run`` method.
* ``st2tests.mocks.sensor.MockSensorWrapper`` - Mock ``SensorWrapper`` class.
* ``st2tests.mocks.sensor.MockSensorService`` - Mock ``SensorService`` class.
  This class mock methods which operate on the datastore items (``list_values``,
  ``get_value``, ``set_value``, ``delete_value``). In addition to that, it also
  allows you to assert that a specific trigger has been dispatched using
  ``assertTriggerDispatched`` method.

Running Tests
-------------

To run all the tests in a particular pack you can use the ``run-pack-tests.sh``
script from the ``st2contrib`` repository as shown below.

```bash
./scripts/run-pack-tests.sh <pack path>
```

Continous Integration
---------------------
