Writing custom Python actions
=============================

In the simplest form, Python action is a module which exposes a class which
inherits from :class:`st2actions.runners.pythonrunner.Action` and implements
a ``run`` method.

Configuration file
------------------

.. note::

    Configuration file should be used to store "static" configuration options
    which don't change between the action runs (e.g. service credentials,
    different constants, etc.).

    For options / parameters which are user defined or change often, you should
    use action parameters which are defined in the metadata file.

Python actions can store arbitrary configuration in the configuration file
which is global to the whole content pack or local to a single action script.

Configuration file which is local to a single action is stored in a file named
``<action_name>_config.json`` and configuration which is global to the whole
content pack is stored inside ``actions/`` directory in a file named
``config.json``.

Configuration file format is JSON. Configuration is automatically parsed in
the action constructor and available via the ``config`` class
attribute (``self.config``).

TODO - link to a sample global and local configuration file

Logging
-------

All the logging inside the action should be performed via the logger which
is specific to this action and available via ``self.logger`` class attribute.

This logger is a standard Python logger from the ``logging`` module so all the
logger methods work as expected (e.g. ``logger.debug``, ``logger.info``, etc).

For example:

.. sourcecode:: python

    def run(self):
        ...
        success = call_some_method()

        if success:
            self.logger.info('Action successfully completed')
        else:
            self.logger.error('Action failed...')
