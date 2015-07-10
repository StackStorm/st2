Development
===========

This page describes StackStorm development process and contains general
guidelines and information on how to contribute to the project.

Contributing
------------

We welcome and appreciate contributions of any kind (code, tests, documentation,
examples, use cases, ...).

If you need help or get stuck at any point during this process, stop by on our
IRC channel (`#stackstorm on freenode <http://webchat.freenode.net/?channels=stackstorm>`_) and we will do our best to
assist you.

For information on contributing an integration pack, please refer to the
:doc:`Create and Contribute a Pack </packs>` page.

Setting up a development environment
------------------------------------

There are multiple ways for you to set up a development environment and get
started with StackStorm development.

The best and easiest approach is to use our Vagrant images which contains all
the dependencies you need to get started. For more information, see
:doc:`Using Vagrant </install/vagrant>`.

Another approach is to install StackStorm and all the dependencies from source
on a server or VM of your liking. For more information about this approach, see
:doc:`Installing StackStorm from sources </install/sources>`.

General contribution guidelines
-------------------------------

* Any non-trivial change must contain corresponding tests. For more
  information, refer to the :doc:`Testing page </development/testing>`.
* All the functions and methods must contain Sphinx docstrings which are used
  to generate the API documentation. We follow the Apache Libcloud project
  docstrings conventions. For more information, refer to the
  `Docstring conventions`_ page.
* If you are adding a new feature, make sure to add a corresponding
  documentation and examples.

Code style guide
----------------

* We follow `PEP8 Python Style Guide`_
* Use 4 spaces for a tab
* Use 100 characters in a line
* Make sure edited file doesn't contain any trailing whitespace
* Make sure that all the source files contains an Apache 2.0 license header.
  For example, see one of the existing Python files with source code.
* You can verify that your modifications don't break any rules by running the
  lint script - ``make flake8``

And most importantly, follow the existing style in the file you are editing and
**be consistent**.

General coding guidelines
-------------------------

Logging
~~~~~~~

Logging is important because it increases the visibility and makes the project
easiest to debug and support.

You are encouraged to generously use the log statements across the code base -
you should log every event which increases the visibility and / or makes the
product easier to debug and support.

Every log statement should also include as much as useful additional context as
possible. This context should be included in the dictionary which is passed via
``extra`` keyword argument to the logger method as shown bellow.

Default log formatters we use include this additional context as part of the
message which makes it easier for user to find the relevant information.

On top of that, we also offer Gelf log formatters which outputs log messages in
GELF format (structured JSON). Users can use this formatter to ship structured
logs to Graylog2, loggly, logstash or a similar service.

Obtaining a reference to the logger object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To obtain a reference to the logger instance you should use
``st2common.log.getLogger`` function as shown bellow. You should use this
function and not the one from the stdlib logging module because we declare a
custom log level and do a couple of other things which are only available on
loggers which are obtained through of version of ``getLogger``.

In most cases, you should do that at the top of the module after the imports
and re-use this logger through that module.

.. sourcecode:: python

    from st2common import log as logging

    LOG = logging.getLogger(__name__)
    LOG.debug('....')

Passing context to the logger
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As noted above, you should always include as much context as possible in the
log messages. Context is provided by passing a dictionary via the ``extra``
keyword argument to the logger method.

This dictionary should contain values which are relevant to the log message in
question (e.g. created / modified database object, user who performed the
action, etc.).

If you are passing an instance of a custom class as a value, you should
implement ``to_dict`` method on that class. This method is responsible for
returning a dictionary representation of this object which can be serialized as
JSON.

Keep in mind that this method is already implement for all of the StackStorm
database object (``ActionDB``, ``RunnerTypeDB``, etc.).

.. sourcecode:: python

    action_db = ...
    user_db = ...
    remote_addr = ...

    extra = {'action_db': action_db, 'user_db': user_db, 'remote_addr': remote_addr}
    LOG.debug('New action has been created. ActionDB.id=%s' % (action_db.id),
              extra=extra)

Using the AUDIT log level
^^^^^^^^^^^^^^^^^^^^^^^^^

StackStorm code declares a custom ``AUDIT`` log level. This log level is to be
when recording CRUD operations on the resources and when performing other
actions which should be logged in the audit log.

For example:

.. sourcecode:: python

    LOG.audit('KeyValuePair updated. KeyValuePair.id=%s' % (kvp_db.id), extra=extra)

Dealing with dates and datetime objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All the ``datetime`` objects which are being used in the codebase should be
timezone aware and represented in UTC. Same goes for storing dates in the
database - timestamps are preferred, but if you can't use a timestamp, stored
dates should be represented in UTC.

If you want to store a timestamp with a microsecond precision you should use
``st2common.fields.ComplexDateTimeField`` field class.

If you want to retrieve ``datetime`` object for current time, you should use
``st2common.util.date.get_datetime_utc_now`` which returns a timezone aware
datetime object in UTC. ``st2common.util.date`` also contains other date and
time related utility functions.

Instantiating model classes
---------------------------

When instantiating mongoengine model classes (e.g. ``ActionDB``, ``RuleDB``,
``SensorTypeDB``, etc.) make sure to pass all the field values as arguments
to the model constructor instead of performing a late assignment of variables
on the class instance.

Good:

.. sourcecode:: python

    action_db = ActionDB(pack='mypack', name='myaction', enabled=True)

Bad:

.. sourcecode:: python

    action_db = ActionDB()
    action_db.pack = 'mypack'
    action_db.name = 'myaction'
    action_db.enabled = True

Passing all the fields as keyword arguments to the constructor means we can
preserve the constructor functionality. On top of that it also makes it more
clear and obvious to the developers when the values are available and allows
us to perform basic "static" analysis on the code.

.. _`PEP8 Python Style Guide`: http://www.python.org/dev/peps/pep-0008/
.. _irc`: http://webchat.freenode.net/?channels=stackstorm
.. _`Docstring conventions`: https://libcloud.readthedocs.org/en/latest/development.html#docstring-conventions
